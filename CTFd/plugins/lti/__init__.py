import base64
import hashlib
import hmac
import time
import urllib.parse
import uuid

import requests
from flask import Blueprint, abort, current_app, redirect, request, url_for
from sqlalchemy import event

from CTFd.models import Solves, Users, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.migrations import upgrade
from CTFd.utils import get_config
from CTFd.utils.user import login_user


def send_grade(url, sourcedid, score, key, secret):
    if not url or not sourcedid:
        return False
    body = f"""<?xml version='1.0' encoding='utf-8'?>
<imsx_POXEnvelopeRequest xmlns='http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'>
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{uuid.uuid4().hex}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <replaceResultRequest>
      <resultRecord>
        <sourcedGUID><sourcedId>{sourcedid}</sourcedId></sourcedGUID>
        <result>
          <resultScore>
            <language>en</language>
            <textString>{score}</textString>
          </resultScore>
        </result>
      </resultRecord>
    </replaceResultRequest>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>"""
    params = {
        "oauth_consumer_key": key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }
    params["oauth_body_hash"] = base64.b64encode(
        hashlib.sha1(body.encode()).digest()
    ).decode()
    all_params = params.copy()
    query = urllib.parse.parse_qsl(
        urllib.parse.urlparse(url).query, keep_blank_values=True
    )
    for k, v in query:
        all_params[k] = v
    param_str = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(all_params[k]), safe='')}"
        for k in sorted(all_params)
    )
    base_elems = [
        "POST",
        urllib.parse.quote(url.split("?")[0], safe=""),
        urllib.parse.quote(param_str, safe=""),
    ]
    base_string = "&".join(base_elems)
    signing_key = f"{secret}&"
    params["oauth_signature"] = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    headers = {"Content-Type": "application/xml"}
    resp = requests.post(url, data=body, params=params, headers=headers)
    return resp.status_code < 300


class LTIResult(db.Model):
    __tablename__ = "lti_results"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    sourcedid = db.Column(db.Text)
    service_url = db.Column(db.Text)
    sent = db.Column(db.Boolean, default=False)


lti_bp = Blueprint("lti", __name__, url_prefix="/lti")


@lti_bp.route("/launch", methods=["POST"])
def lti_launch():
    key = get_config("lti_consumer_key")
    secret = get_config("lti_consumer_secret")
    consumer = request.form.get("oauth_consumer_key")
    if consumer != key:
        abort(403)
    email = request.form.get("lis_person_contact_email_primary")
    name = request.form.get("lis_person_name_full") or email
    user = Users.query.filter_by(email=email).first()
    if user is None:
        user = Users(name=name, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    result = LTIResult(
        user_id=user.id,
        sourcedid=request.form.get("lis_result_sourcedid"),
        service_url=request.form.get("lis_outcome_service_url"),
    )
    db.session.add(result)
    db.session.commit()
    return redirect(url_for("challenges.listing"))


def after_solve(mapper, connection, solve):
    app = current_app._get_current_object()
    with app.app_context():
        key = get_config("lti_consumer_key")
        secret = get_config("lti_consumer_secret")
        result = LTIResult.query.filter_by(user_id=solve.user_id, sent=False).first()
        if result:
            success = send_grade(result.service_url, result.sourcedid, 1, key, secret)
            if success:
                result.sent = True
                db.session.commit()


def load(app):
    upgrade(plugin_name="lti")
    register_plugin_assets_directory(app, base_path="/plugins/lti/assets/")
    app.register_blueprint(lti_bp)
    event.listen(Solves, "after_insert", after_solve)
