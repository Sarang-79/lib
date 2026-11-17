# Library Desk

A lightweight library-management app built with Flask and SQLite. Add books to
the catalog, search by title/author/ISBN, check copies out to readers, and
record returns. The dashboard shows catalog and active-loan totals.

## Run locally

Requires Python 3.9 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The SQLite database is created at
`instance/library.sqlite`; set `LIBRARY_DATABASE` to use another location.
Set `FLASK_SECRET_KEY` to a private value when deploying.

Run the tests with:

```powershell
python -m unittest discover -s tests -v
```

## Jenkins and GitHub

Jenkins is a separate application; opening the library URL does not start it.
On Windows, install Jenkins LTS using the official Windows installer and
complete its initial setup. To start Jenkins, open the Windows Services app
(press **Win+R**, type `services.msc`, and press **Enter**), find **Jenkins**,
and choose **Start**. Then open <http://localhost:8080> in a browser on the
same computer. If Jenkins was configured to use a different port, use that
port instead.

To connect Jenkins to GitHub:

1. Push this project, including `Jenkinsfile`, to a GitHub repository.
2. In Jenkins, select **New Item**, enter a job name, choose **Pipeline**, and
   select **OK**.
3. In the job's **Pipeline** section, choose **Pipeline script from SCM**,
   select **Git**, enter the repository URL, add credentials if the repository
   is private, select the branch, and set **Script Path** to `Jenkinsfile`.
4. Save the job. Select **Build Now** to run it manually, then open the build
   in **Build History** to see its test results.

Make sure the Jenkins agent has Python 3 and pip available. The Jenkinsfile
polls GitHub every five minutes and also schedules one build per day.

To start the library app, use the local run steps above in a terminal and keep
that terminal open. Then browse to <http://127.0.0.1:5000>. To open Jenkins,
start its Windows service separately and browse to <http://localhost:8080>.
