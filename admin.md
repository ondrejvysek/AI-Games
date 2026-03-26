# Admin Documentation - Copilot Chat Website

## Project Overview
This is a static website built with HTML5, Bootstrap 5.3, and custom CSS. It is designed to be lightweight, fast, and easy to maintain without a complex backend or CMS.

### Folder Structure
- `css/`: Contains `style.css` (global styles).
- `js/`: Contains `main.js` (navigation logic).
- `img/`: Place for images.
- `media/`: Place for video files.
- `en/`: English version of the site.
- `cs/`: Czech version.
- `sk/`: Slovak version.

## Maintenance

### 1. Editing Content
To change text or images, open the corresponding `.html` file in a text editor (VS Code, Notepad++, etc.).
- **Landing Page:** `index.html`
- **Challenge Page:** `challenge.html`
- **News:** `news.html`
- **Privacy:** `privacy.html`
- **About:** `about.html`

**Multilingual Support:**
When you update content in English (`en/`), remember to manually update the corresponding files in `cs/` and `sk/`.

### 2. Adding Blog Posts
To add a new post to the **News** page:
1. Open `news.html`.
2. Locate the `<div class="row g-4">` section.
3. Copy an existing `.col-md-4` block (the entire card).
4. Paste it at the beginning of the row.
5. Update the image `src`, title, text, and date.

### 3. Managing Videos
The site uses a standard HTML5 video player.

**Preparation:**
Before uploading, ensure your video is in a web-friendly format (MP4 with H.264 video and AAC audio).
Use a tool like `ffmpeg` to transcode:
```bash
ffmpeg -i input_video.mov -vcodec libx264 -crf 23 -preset fast -acodec aac -b:a 128k output_video.mp4
```

**Uploading:**
1. Place the `.mp4` file in the `media/` folder (create it if it doesn't exist).
2. In the HTML file, update the `<video>` tag:
```html
<video controls poster="path/to/poster_image.jpg">
    <source src="../media/output_video.mp4" type="video/mp4">
    Your browser does not support the video tag.
</video>
```

**Authentication Note:**
Since this is a static site, there is no backend to authenticate users for private videos. If you need secure video access (e.g., for the 30-day challenge emails), consider hosting the videos on a secure platform (Microsoft Stream, Vimeo with password) and embedding them, or using a token-based access system with a backend service.

### 4. Brevo Integration (Mailing List)
The "30-Day Challenge" form in `challenge.html` is currently a placeholder.
To connect it to Brevo:
1. Create a form in your Brevo account.
2. Get the HTML form code or the form Action URL.
3. Update the `<form action="...">` attribute in `challenge.html` with your Brevo URL.
4. Ensure the input `name` attributes match what Brevo expects (usually `EMAIL`).

### 5. Deployment
This site can be hosted on any static web hosting service:
- **Azure Static Web Apps** (Recommended for Microsoft ecosystem).
- **GitHub Pages**.
- **Netlify / Vercel**.

Simply upload the entire project folder to the root of your web server.
