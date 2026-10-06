# Vertusma — Namecheap Shared Hosting Deployment

This package is a dependency-free **WSGI** conversion of the Vertusma website. It is designed for **cPanel → Setup Python App** and Passenger on Namecheap Shared Hosting.

## Recommended URL

Install it at either:

- the root of the main domain, for example `https://example.com`, or
- the root of a subdomain, for example `https://beta.example.com`.

Do not install it in a path such as `example.com/vertusma`; the frontend currently uses root-relative URLs.

## 1. Create the Python application

In Namecheap cPanel, open **Software → Setup Python App** and click **Create Application**.

Use:

```text
Python version: 3.12 or another supported Python 3 version
Application root: vertusma_app
Application URL: your domain or subdomain
Application startup file: passenger_wsgi.py
Application entry point: application
```

Click **Create**.

## 2. Upload the website

Open **Files → File Manager** and navigate to:

```text
/home/YOUR_CPANEL_USERNAME/vertusma_app/
```

Upload the supplied Vertusma deployment ZIP into that directory and extract it there.

The result must look like:

```text
vertusma_app/
├── app.py
├── passenger_wsgi.py
├── requirements.txt
├── public/
└── data/
```

Do not leave everything inside an additional folder.

## 3. No package installation is required

This edition uses Python's standard library only. You do not need Flask, Django, Node.js, Docker, or a Pip installation.

The included `requirements.txt` intentionally contains no packages.

## 4. Add environment variables

Return to **Setup Python App** and add:

```text
ADMIN_EMAIL=your-real-admin-email@example.com
ADMIN_PASSWORD=use-a-long-unique-password
COOKIE_SECURE=1
SESSION_MAX_AGE=43200
DATABASE_PATH=/home/YOUR_CPANEL_USERNAME/vertusma_app/data/vertusma.db
```

Replace `YOUR_CPANEL_USERNAME` with the username displayed in cPanel.

After adding the variables, click **Update/Save**, then **Restart**.

Never publish the website with the demonstration password.

## 5. Permissions

Files uploaded through your own cPanel account normally have the correct ownership. Recommended permissions:

```text
Folders: 755
Python, HTML, CSS and JavaScript files: 644
Database file: 644
```

The `data` folder must be writable by your hosting account. Do not use permission `777`.

## 6. Enable HTTPS

Enable Namecheap SSL/AutoSSL for the selected domain before using the admin portal.

`COOKIE_SECURE=1` protects the admin login cookie by allowing it only over HTTPS. For temporary HTTP testing only, set it to `0`, restart the application, then restore it to `1` after SSL is working.

## 7. Test the live installation

Open these addresses:

```text
https://yourdomain.com/api/health
https://yourdomain.com/
https://yourdomain.com/admin
```

The health endpoint should return JSON containing:

```json
{"ok":true,"service":"Vertusma Property Management","runtime":"WSGI"}
```

Then test:

1. Submit an inquiry from the public contact form.
2. Log in to `/admin`.
3. Confirm the inquiry appears.
4. Add and edit a property.
5. Restart the Python app.
6. Confirm the property and inquiry remain saved.

The SQLite database is automatically created and seeded on the application's first start. If an earlier Vertusma database already exists, this version performs an in-place schema upgrade and preserves existing properties and inquiries.

## Updating the website

Upload changed files into the same application root and click **Restart** in Setup Python App.

Do not overwrite or delete:

```text
data/vertusma.db
public/uploads/
```

unless you intentionally want to erase saved website content/data or uploaded media.

## Database backup

Regularly download:

```text
/home/YOUR_CPANEL_USERNAME/vertusma_app/data/vertusma.db
```

That database contains the live portfolio, inquiries, website settings, custom sections, custom pages, and CMS content.

Also back up:

```text
/home/YOUR_CPANEL_USERNAME/vertusma_app/public/uploads/
```

That folder contains images uploaded through the admin CMS. A complete restore requires both the database and uploaded-image folder.

## Troubleshooting

### Internal Server Error

Check that Setup Python App uses:

```text
Startup file: passenger_wsgi.py
Entry point: application
```

Then restart the application and inspect the Python application log in cPanel.

### Admin login immediately returns to the login page

Confirm the site opens with `https://` and `COOKIE_SECURE=1`. For HTTP-only testing, temporarily use `COOKIE_SECURE=0`.

### Database is not writable

Confirm that the `DATABASE_PATH` contains the correct cPanel username and that the `data` folder belongs to your hosting account.
