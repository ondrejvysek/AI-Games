document.addEventListener('DOMContentLoaded', () => {
    // Mobile Menu Toggle
    const toggler = document.querySelector('.navbar-toggler');
    const menu = document.querySelector('.navbar-menu-pill');

    if (toggler && menu) {
        toggler.addEventListener('click', () => {
            menu.classList.toggle('show');
            const expanded = toggler.getAttribute('aria-expanded') === 'true' || false;
            toggler.setAttribute('aria-expanded', !expanded);
        });
    }

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (menu && menu.classList.contains('show') && !menu.contains(e.target) && !toggler.contains(e.target)) {
            menu.classList.remove('show');
            toggler.setAttribute('aria-expanded', 'false');
        }
    });

    // Active Link Highlighting
    const currentPath = window.location.pathname;
    const links = document.querySelectorAll('.nav-link');

    links.forEach(link => {
        const href = link.getAttribute('href');
        // Handle relative paths or exact matches
        if (href === currentPath ||
           (currentPath === '/' && href === 'index.html') ||
           (currentPath.endsWith(href))) {
            link.classList.add('active');
        }
    });

    // Custom Video Player Logic
    const players = document.querySelectorAll('.custom-video-player');

    players.forEach(player => {
        const video = player.querySelector('video');
        const overlay = player.querySelector('.video-overlay');
        const playBtnLarge = player.querySelector('.play-btn-large');
        const playBtnSmall = player.querySelector('.play-toggle i');
        const progressBar = player.querySelector('.progress-bar');
        const progressContainer = player.querySelector('.progress-container');
        const muteBtn = player.querySelector('.mute-toggle i');
        const fullscreenBtn = player.querySelector('.fullscreen-toggle');

        if (!video) return;

        // Obfuscate Video Source (Simple Blob technique for small files)
        const originalSrc = video.getAttribute('data-src');
        if (originalSrc) {
            fetch(originalSrc)
                .then(response => response.blob())
                .then(blob => {
                    const blobUrl = URL.createObjectURL(blob);
                    video.src = blobUrl;
                })
                .catch(err => {
                    console.error("Failed to load video blob, falling back to direct source", err);
                    video.src = originalSrc;
                });
        }

        const togglePlay = () => {
            if (video.paused) {
                video.play();
                player.classList.add('playing');
                player.classList.remove('paused');
                if(playBtnSmall) playBtnSmall.className = 'fas fa-pause';
            } else {
                video.pause();
                player.classList.remove('playing');
                player.classList.add('paused');
                if(playBtnSmall) playBtnSmall.className = 'fas fa-play';
            }
        };

        // Event Listeners
        if(playBtnLarge) playBtnLarge.addEventListener('click', togglePlay);
        if(video) video.addEventListener('click', togglePlay);
        if(player.querySelector('.play-toggle')) {
            player.querySelector('.play-toggle').addEventListener('click', togglePlay);
        }

        // Update Progress
        video.addEventListener('timeupdate', () => {
            const percent = (video.currentTime / video.duration) * 100;
            if(progressBar) progressBar.style.width = `${percent}%`;
        });

        // Seek
        if(progressContainer) {
            progressContainer.addEventListener('click', (e) => {
                const rect = progressContainer.getBoundingClientRect();
                const pos = (e.clientX - rect.left) / rect.width;
                video.currentTime = pos * video.duration;
            });
        }

        // Mute
        if(player.querySelector('.mute-toggle')) {
            player.querySelector('.mute-toggle').addEventListener('click', () => {
                video.muted = !video.muted;
                if(muteBtn) muteBtn.className = video.muted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
            });
        }

        // Fullscreen
        if(fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    player.requestFullscreen().catch(err => {
                        console.log(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
                    });
                } else {
                    document.exitFullscreen();
                }
            });
        }

        // Prevent Right Click (Context Menu)
        video.addEventListener('contextmenu', (e) => e.preventDefault());
    });

    // Challenge Page Logic (Week Tabs)
    const weekTabs = document.querySelectorAll('.week-tab');
    const weekContentTitle = document.getElementById('week-content-title');
    const weekContentDesc = document.getElementById('week-content-desc');
    const weekPromptText = document.getElementById('week-prompt-text');

    const weekData = {
        1: {
            title: "Week 1: Foundations & Quick Wins",
            desc: "Start with simple, high-impact prompts. Learn to summarize emails and draft quick replies.",
            prompt: "Summarize this email into 3 bullet points and suggest a follow-up action.\n\n[Insert Email Here]"
        },
        2: {
            title: "Week 2: Writing & Communication",
            desc: "Focus on tone and style. Draft professional emails, newsletters, and internal announcements.",
            prompt: "Draft a professional email to the team about the new project timeline.\nTone: Encouraging but firm.\nKey dates: Start Monday, End Q3."
        },
        3: {
            title: "Week 3: Analysis & Synthesis",
            desc: "Deep dive into data. Summarize meetings, analyze reports, and extract key insights.",
            prompt: "Analyze these meeting notes. What are the top 3 risks mentioned?\n\n[Insert Notes]"
        },
        4: {
            title: "Week 4: Advanced Workflows",
            desc: "Chain prompts together. Build complex workflows for project management and creativity.",
            prompt: "Act as a senior project manager. Create a risk mitigation plan for the risks identified above."
        },
        5: { // After challenge
            title: "Beyond 30 Days",
            desc: "Integrate Copilot into your daily routine. Explore Copilot in Excel and PowerPoint.",
            prompt: "Create a 5-slide presentation outline based on the project plan we just created."
        }
    };

    weekTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            // Remove active class from all
            weekTabs.forEach(t => t.classList.remove('active', 'bg-primary', 'text-white'));
            weekTabs.forEach(t => t.classList.add('bg-white', 'text-dark'));

            // Add active class to clicked
            tab.classList.remove('bg-white', 'text-dark');
            tab.classList.add('active', 'bg-primary', 'text-white');

            // Update Content
            const weekId = tab.getAttribute('data-week');
            const data = weekData[weekId];
            if (data) {
                if(weekContentTitle) weekContentTitle.textContent = data.title;
                if(weekContentDesc) weekContentDesc.textContent = data.desc;
                if(weekPromptText) weekPromptText.textContent = data.prompt;
            }
        });
    });

    // Copy Prompt Button
    const copyBtn = document.getElementById('copy-prompt-btn');
    if (copyBtn && weekPromptText) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(weekPromptText.textContent).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                }, 2000);
            });
        });
    }
});
