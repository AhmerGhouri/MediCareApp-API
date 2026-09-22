# Response changes and deployment checks

Empty collection reads now return HTTP 200 with the existing collection key and
an empty array (nine patient endpoints). Patient metadata is null when no row
exists; no new patient query or ownership policy was introduced. Consultation
access denial remains an error, separate from an authorized empty history.

Errors retain success=false, error_type and message, and add a stable code.
Validation uses an errors field map without input, raw context or submitted values.
Database failures are server errors with safe messages, not raw database text.

The app uses request-otp (mobile, email), then verify-otp-and-reset (mobile, email,
otp_code, new_password). Both status=success and success=true are accepted during
rollout. OTP SQL alias and ten-minute expiry were corrected; SMTP errors now
propagate instead of producing false success. The app no longer uses demo codes.

Explicitly deferred by the owner: patient-ownership checks on lab/upcoming/combined
reads, and authorization of the separate reset-password endpoint. These remain
security risks. This change is not a security sign-off.

Run python3 -B -m unittest discover -s tests -v. Tests isolate handler functions
with fake dependencies, without starting the scheduler, database, or email service.
Before deployment, run ASGI tests with installed dependencies and staging Oracle:
empty/nonempty reads, access denial, invalid login, malformed input, OTP delivery,
wrong/expired OTP, successful reset, booking conflict and notification failure.
No deployment or production database changes are performed by this patch.
