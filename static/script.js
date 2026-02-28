// Navigation Toggle for Mobile
const hamburger = document.querySelector('.hamburger');
const navLinks = document.querySelector('.nav-links');

if (hamburger) {
    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    // Close menu when clicking on a link
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });
}

// Contact Form Submission
const contactForm = document.getElementById('contactForm');

if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById('submitBtn');
        const formMessage = document.getElementById('formMessage');

        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';

        // Get form data
        const formData = {
            name: document.getElementById('name').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            location: document.getElementById('location').value,
            role: document.getElementById('role').value,
            date: document.getElementById('date').value,
            eventType: document.getElementById('eventType').value,
            weddingInfo: document.getElementById('weddingInfo').value,
            howFound: document.getElementById('howFound').value
        };

        try {
            const response = await fetch('/send_email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                formMessage.textContent = 'Thank you! Your message has been sent successfully. We\'ll get back to you soon!';
                formMessage.className = 'form-message success';
                formMessage.style.display = 'block';
                contactForm.reset();
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            formMessage.textContent = 'Sorry, there was an error sending your message. Please try again or email us directly.';
            formMessage.className = 'form-message error';
            formMessage.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send Message';

            // Hide message after 5 seconds
            setTimeout(() => {
                formMessage.style.display = 'none';
            }, 5000);
        }
    });
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Lightbox Functionality
class Lightbox {
    constructor() {
        this.lightbox = null;
        this.lightboxImage = null;
        this.currentIndex = 0;
        this.images = [];
        this.init();
    }

    init() {
        // Create lightbox HTML structure
        this.createLightbox();

        // Add click listeners to all gallery images
        const galleryImages = document.querySelectorAll('.set-gallery-grid img, .set-gallery-masonry img');

        if (galleryImages.length > 0) {
            // Store all image sources
            this.images = Array.from(galleryImages).map(img => img.src);

            // Add click event to each image
            galleryImages.forEach((img, index) => {
                img.addEventListener('click', () => {
                    this.open(index);
                });
            });
        }
    }

    createLightbox() {
        // Create lightbox container
        const lightboxHTML = `
            <div class="lightbox" id="lightbox">
                <span class="lightbox-close">&times;</span>
                <span class="lightbox-prev">&#10094;</span>
                <span class="lightbox-next">&#10095;</span>
                <div class="lightbox-content">
                    <img class="lightbox-image" id="lightboxImage" src="" alt="Gallery Image">
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', lightboxHTML);

        // Get elements
        this.lightbox = document.getElementById('lightbox');
        this.lightboxImage = document.getElementById('lightboxImage');

        // Add event listeners
        this.lightbox.addEventListener('click', (e) => {
            if (e.target === this.lightbox) {
                this.close();
            }
        });

        document.querySelector('.lightbox-close').addEventListener('click', () => {
            this.close();
        });

        document.querySelector('.lightbox-prev').addEventListener('click', (e) => {
            e.stopPropagation();
            this.prev();
        });

        document.querySelector('.lightbox-next').addEventListener('click', (e) => {
            e.stopPropagation();
            this.next();
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.lightbox.classList.contains('active')) return;

            if (e.key === 'Escape') this.close();
            if (e.key === 'ArrowLeft') this.prev();
            if (e.key === 'ArrowRight') this.next();
        });

        // Prevent image click from closing lightbox
        this.lightboxImage.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    open(index) {
        this.currentIndex = index;
        this.lightboxImage.src = this.images[index];
        this.lightbox.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent scrolling
    }

    close() {
        this.lightbox.classList.remove('active');
        document.body.style.overflow = ''; // Re-enable scrolling
    }

    next() {
        this.currentIndex = (this.currentIndex + 1) % this.images.length;
        this.lightboxImage.src = this.images[this.currentIndex];
    }

    prev() {
        this.currentIndex = (this.currentIndex - 1 + this.images.length) % this.images.length;
        this.lightboxImage.src = this.images[this.currentIndex];
    }
}

// Initialize lightbox when DOM is loaded
if (document.querySelector('.set-gallery-grid') || document.querySelector('.set-gallery-masonry')) {
    new Lightbox();
}

window.addEventListener('scroll', () => {
    const nav = document.querySelector('nav');

    if (window.scrollY > 50) {
        nav.classList.add('scrolled');
    } else {
        nav.classList.remove('scrolled');
    }
});
// Parallax Effect - Super Simple
window.addEventListener('scroll', function() {
    const heroBg = document.querySelector('.hero-bg');
    if (heroBg) {
        const scrolled = window.pageYOffset;
        heroBg.style.transform = `translateY(${scrolled * 0.5}px)`;
    }
});