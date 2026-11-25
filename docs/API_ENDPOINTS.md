# HireFlow REST API

Base URL (local): `http://127.0.0.1:8000/api/`

## Authentication
1. `POST /api/auth/login/` returns a token.
2. Send it on every other request as a header: `Authorization: Token <your token>`.
3. The user is always taken from the token. **Never send a candidate id**; any such value is ignored.

## Error format (every error looks like this)
```json
{ "error": { "status": 409, "code": "duplicate_application", "message": "You have already applied for this job.", "details": null } }
```
For validation errors `code` is `invalid` and `details` lists the field problems.

| Status | Meaning |
|---|---|
| 200 / 201 | OK / created |
| 400 | Validation error or a business rule was broken |
| 401 | Missing or invalid token |
| 403 | Logged in but not allowed (wrong role or another company's data) |
| 404 | Not found |
| 409 | Conflict, for example a duplicate application |

Lists are paginated: `{ "count": 25, "next": "...", "previous": null, "results": [ ... ] }` (10 per page, use `?page=2`).

## Endpoints

### Authentication
| Method and path | Who | Body | Result |
|---|---|---|---|
| `POST /api/auth/register/` | anyone | `role` (candidate or recruiter), `full_name`, `email`, `password`, recruiters also `company_name` (optional `designation`, `phone`) | 201 `{token, user}` |
| `POST /api/auth/login/` | anyone | `email`, `password` | 200 `{token, user}`; 401 if wrong |
| `POST /api/auth/logout/` | logged in | none | 200, token is deleted |

### Jobs
| Method and path | Who | Notes |
|---|---|---|
| `GET /api/jobs/` | anyone | Public jobs only (published, not expired, verified company, not hidden). Query: `q`, `location`, `employment_type`, `experience`, `sort` (newest, deadline, salary, title), `page` |
| `GET /api/jobs/<id>/` | anyone | 404 if the job is not public (the owning company's recruiters can still read it) |
| `POST /api/jobs/` | recruiter | Creates a **draft**. Body: `title`, `description`, `location`, `deadline` (YYYY-MM-DD), `experience_min`, `experience_max`, optional `responsibilities`, `employment_type`, `salary_min`, `salary_max`, `salary_currency`, `skills` (list of names), `status` |
| `PATCH /api/jobs/<id>/` | recruiter of the owning company | Any field above. `"status": "published"` / `"paused"` / `"closed"` changes the job state. Other companies get 403 |

### Applications
| Method and path | Who | Notes |
|---|---|---|
| `POST /api/applications/` | candidate | Body: `job_id`, `resume_id`, optional `cover_letter`. 201; 409 duplicate; 400 closed/expired job or someone else's resume |
| `GET /api/me/applications/` | candidate | Own applications. Optional `?status=shortlisted` |
| `GET /api/recruiter/jobs/<id>/applications/` | recruiter of that job's company | Applicants. 403 for other companies |
| `PATCH /api/applications/<id>/status/` | recruiter of that job's company | Body: `status` (under_review, shortlisted, interview_completed, selected, rejected), optional `note`. Invalid transitions return 400. A history row and a candidate notification are created |

### Interviews
| Method and path | Who | Notes |
|---|---|---|
| `POST /api/applications/<id>/interviews/` | recruiter of that company | Body: `scheduled_at` (ISO 8601, future), `mode` (online/phone/onsite), `meeting_details` (required for online), optional `duration_minutes`, `interviewer_name`. Application must be shortlisted (or later). Application becomes *Interview Scheduled* |

### Notifications
| Method and path | Who | Notes |
|---|---|---|
| `GET /api/me/notifications/` | logged in | Own notifications, newest first. `?unread=1` for unread only |

## Testing with Postman
1. Start the server (`python manage.py runserver`) and load demo data (`python manage.py seed_demo`).
2. In Postman create a **collection** called HireFlow and a collection **variable** `base` = `http://127.0.0.1:8000/api`.
3. Request 1: `POST {{base}}/auth/login/`, Body > raw > JSON:
   `{"email": "candidate@hireflow.test", "password": "Candidate@12345"}`. Copy the `token`.
4. On the collection, open **Authorization**, choose **API Key**: key `Authorization`, value `Token <paste token>`, add to **Header**.
5. Try `GET {{base}}/jobs/?q=django`, `GET {{base}}/me/applications/`, `GET {{base}}/me/notifications/`.
6. Log in as `recruiter@hireflow.test` / `Recruiter@12345`, replace the token, then try `POST {{base}}/jobs/`
   and `GET {{base}}/recruiter/jobs/1/applications/`.
7. Check the error cases: apply twice (409), use the candidate token on a recruiter endpoint (403), no token (401).
