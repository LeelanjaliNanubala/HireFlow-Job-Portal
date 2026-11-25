# HireFlow user guide

Open `http://127.0.0.1:8000/` after starting the server. Demo accounts (created by `python manage.py seed_demo`):

| Role | Email | Password |
|---|---|---|
| Administrator | admin@hireflow.test | Admin@12345 |
| Recruiter (verified company) | recruiter@hireflow.test | Recruiter@12345 |
| Recruiter (company waiting for verification) | recruiter2@hireflow.test | Recruiter@12345 |
| Candidate | candidate@hireflow.test | Candidate@12345 |
| Candidate | candidate2@hireflow.test | Candidate@12345 |

These are demo accounts. Never create them on a real website.

## Candidate
1. **Sign up** (Sign up > I'm looking for a job). You land on your profile.
2. Fill **Profile**, **Education**, **Experience**, **Skills** (tabs at the top). The progress bar shows completeness.
3. **Resumes**: upload a PDF, DOC or DOCX up to 5 MB. Resumes are private.
4. **Find jobs**: search by keyword, location, type and experience; sort; open a job.
5. **Apply**: choose a resume, optionally write a cover letter, press *Apply now*. Duplicate applications are blocked.
6. **Save job** keeps a job in *Saved*.
7. **Applications** shows every status change (timeline). You can **withdraw** before a final decision.
8. **Interviews** lists dates, mode and meeting links. The bell icon shows notifications.

## Recruiter
1. **Sign up** (Sign up > I'm hiring). A company is created with status *Pending*.
2. Complete the **Company** profile. An administrator must **verify** the company before you can publish jobs.
3. **My jobs > Post a job** saves a draft. Use *Publish*, *Pause*, *Close* (and *Reopen*) from the jobs table.
4. **Applicants** lists applications for a job. *Review* shows the candidate profile, resume download and history.
5. Update the **status** (Under review, Shortlisted, Rejected, Selected ...). The candidate is notified.
6. **Schedule interview** (for shortlisted candidates). Edit an interview later to change it, mark it completed and
   add private **feedback** and a rating. Candidates never see feedback.
7. The **Dashboard** shows live numbers and charts for your company only.

## Administrator
Log in and open **Admin dashboard**:
* **Users**: search, activate or deactivate accounts (you cannot deactivate yourself).
* **Companies**: Verify, Reject or set Pending with an optional note. Recruiters are notified.
* **Jobs**: hide a job with a reason (it disappears from public search), unhide, feature or unfeature.
* **Applications**: read-only monitoring with filters.
* **Analytics** and **Audit log**: platform charts and a record of every admin action.

The technical Django admin panel is at `/django-admin/` (for superusers).

## Password reset
Use *Forgot password?* on the login page. Email is disabled by default, so the reset link is **printed in the
terminal** where `runserver` is running. Copy it into the browser.
