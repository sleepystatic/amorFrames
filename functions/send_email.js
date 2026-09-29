// Cloudflare Pages Function -> answers POST /send_email, the same path
// static/script.js already posts JSON to, so the frontend is unchanged.
//
// Secrets are set with `wrangler pages secret put` (see README-DEPLOY.md):
//   MAILGUN_API_KEY  MAILGUN_DOMAIN  MAIL_DEFAULT_SENDER  MAIL_RECIPIENT
//
// If the Mailgun account is in the EU region, change api.mailgun.net below
// to api.eu.mailgun.net.

export async function onRequestPost({ request, env }) {
  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });

  try {
    const d = await request.json();
    const v = (key) => d[key] || 'N/A';

    const text = `NEW CONTACT FORM SUBMISSION - AMOR FRAMES

CLIENT INFORMATION:
Name: ${v('name')}
Email: ${v('email')}
Phone: ${v('phone')}
Location: ${v('location')}

EVENT DETAILS:
Role: ${v('role')}
Date Needed: ${v('date')}
Event Type: ${v('eventType')}

WEDDING VISION & REQUIREMENTS:
${v('weddingInfo')}

HOW THEY FOUND US:
${v('howFound')}`;

    const form = new FormData();
    form.append('from', `Amor Frames <${env.MAIL_DEFAULT_SENDER}>`);
    form.append('to', env.MAIL_RECIPIENT);
    form.append('subject', `New Wedding Inquiry from ${v('name')}`);
    form.append('text', text);
    // Lets the reply go straight back to the couple.
    if (d.email) form.append('h:Reply-To', d.email);

    const res = await fetch(
      `https://api.mailgun.net/v3/${env.MAILGUN_DOMAIN}/messages`,
      {
        method: 'POST',
        headers: { Authorization: 'Basic ' + btoa(`api:${env.MAILGUN_API_KEY}`) },
        body: form,
      }
    );

    if (!res.ok) {
      console.log('Mailgun error:', await res.text());
      return json({ success: false, message: 'Email failed to send' }, 502);
    }
    return json({ success: true, message: 'Email sent successfully!' });
  } catch (err) {
    console.log('Function error:', err);
    return json({ success: false, message: 'Server error' }, 500);
  }
}
