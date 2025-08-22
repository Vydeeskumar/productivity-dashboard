from datetime import datetime, timedelta
import traceback

from django.conf import settings
from django.shortcuts import render
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def home(request):
    sheets = []
    calendar_events = []
    tasks = []
    error_message = None

    if request.user.is_authenticated:
        try:
            creds = Credentials(
                token=getattr(request.user, "access_token", None),
                refresh_token=getattr(request.user, "refresh_token", None),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=settings.GOOGLE_SCOPES,
            )

            drive_service = build("drive", "v3", credentials=creds)
            calendar_service = build("calendar", "v3", credentials=creds)
            tasks_service = build("tasks", "v1", credentials=creds)

            # Sheets via Drive (list spreadsheets)
            try:
                sheets_results = drive_service.files().list(
                    q="mimeType='application/vnd.google-apps.spreadsheet'",
                    pageSize=15,
                    fields="files(id, name)",
                ).execute()
                sheets = sheets_results.get("files", []) or []
            except Exception as e:
                traceback.print_exc()
                error_message = (error_message or "") + f"\nSheets error: {e}"

            # Calendar: next 7 days
            try:
                now = datetime.utcnow().isoformat() + "Z"
                week_from_now = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
                events_result = calendar_service.events().list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=week_from_now,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()
                calendar_events = events_result.get("items", []) or []
            except Exception as e:
                traceback.print_exc()
                error_message = (error_message or "") + f"\nCalendar error: {e}"

            # Tasks: first few lists, incomplete tasks
            try:
                tasklists_result = tasks_service.tasklists().list().execute()
                task_lists = tasklists_result.get("items", []) or []

                all_tasks = []
                for task_list in task_lists[:3]:
                    tasks_result = tasks_service.tasks().list(
                        tasklist=task_list["id"],
                        maxResults=10,
                        showCompleted=False,
                    ).execute()
                    list_tasks = tasks_result.get("items", []) or []
                    for t in list_tasks:
                        t["list_name"] = task_list.get("title", "Tasks")
                        all_tasks.append(t)
                tasks = all_tasks
            except Exception as e:
                traceback.print_exc()
                error_message = (error_message or "") + f"\nTasks error: {e}"

        except RefreshError:
            error_message = "Your Google session expired. Please log out and log in again."
        except Exception as e:
            traceback.print_exc()
            error_message = f"Unexpected error: {e}"

    context = {
        "sheets": sheets,
        "calendar_events": calendar_events,
        "tasks": tasks,
        "error_message": error_message,
    }
    return render(request, "dashboard/home.html", context)
