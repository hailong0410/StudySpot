# StudySpot hosted pilot

The Flask app and hosted pilot share the verified campus catalog, discovery
pages, styles and five-second observation panel. The hosted Worker implements
the observation endpoints on a durable D1 database so visitors share one feed.
The Worker permits embedding on its own origin and in the ChatGPT preview
at https://chatgpt.com. The form still requires the StudySpot origin.
The two environments have separate report databases.

Set a secret named REPORT_SOURCE_KEY in the hosting environment. Production
POST requests accept only same-origin URL-encoded form data and validate all
fields. The network cooldown uses an HMAC of the Cloudflare-provided IP
address. The service stores no raw IP in its database. On a later write it
clears expired source keys, and reads omit observations older than seven days.
Each room starts with zero observations.

To build in a configured Sites checkout, install the pinned Python runtime
dependencies, create .openai/hosting.json with the assigned project_id and
d1 set to DB, and run:

    python hosting/build.py
    node --test hosting/test-worker.mjs

The test uses a separate in-memory database. Deploy the build with
hosting/drizzle as the migration directory in the hosting checkout.
