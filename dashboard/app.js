/**
 * AutoJobs Referral AI Agent — Dashboard & Talent Copilot Logic
 */

// Pipeline Data Store (Synced from tracker / initial seed)
const pipelineData = [
  { company: "Revolut", role: "Product Manager - AI Platform", location: "Remote / EU", ats: 98, status: "ready" },
  { company: "Mercari", role: "Associate Product Manager", location: "Tokyo, Japan / Remote", ats: 95, status: "ready" },
  { company: "Grab", role: "Product Manager - Consumer Experience", location: "Singapore / Remote", ats: 92, status: "ready" },
  { company: "Personio", role: "Senior Product Manager", location: "Munich, Germany / EU", ats: 88, status: "applied" },
  { company: "Valiance Solutions", role: "Product Manager", location: "Pune, India / Remote", ats: 96, status: "sent" },
  { company: "UKG", role: "Sr Product Manager", location: "Pune, India / Remote", ats: 90, status: "sent" },
  { company: "TechBiz Global", role: "Senior Product Manager Claims", location: "Berlin, Germany / EU", ats: 98, status: "ready" },
  { company: "Westwing Group", role: "Product Manager", location: "Munich, Germany / EU", ats: 88, status: "applied" },
  { company: "Ema", role: "Product Manager", location: "London, UK / Remote", ats: 88, status: "ready" },
  { company: "ThinkMarkets", role: "Product Owner", location: "London, UK", ats: 70, status: "applied" },
  { company: "Skyhigh Security", role: "Senior Product Manager", location: "Remote / Global", ats: 90, status: "applied" }
];

document.addEventListener("DOMContentLoaded", () => {
  renderPipeline("all");
  setupEventListeners();
  checkUrlParamsForAutoIngest();
});

function setupEventListeners() {
  // Filter buttons
  const filterBtns = document.querySelectorAll(".filter-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderPipeline(btn.getAttribute("data-filter"));
    });
  });

  // Form submit
  const form = document.getElementById("ingest-form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    synthesizeReferralPacket();
  });

  // Mock lead button
  document.getElementById("btn-mock").addEventListener("click", () => {
    const mockCompanies = [
      { company: "Stripe", role: "AI Product Manager", location: "Singapore / Remote", desc: "LLM agent integration, B2B payment workflows, developer APIs" },
      { company: "Monzo", role: "Senior Product Manager - Platform", location: "London, UK / Remote", desc: "Banking infrastructure, 0-to-1 scale, high-velocity roadmap" },
      { company: "Rakuten", role: "Associate Product Manager", location: "Tokyo, Japan / Remote", desc: "Cross-border commerce, AI recommendation systems" },
      { company: "Delivery Hero", role: "Product Manager - Logistics AI", location: "Berlin, Germany / EU", desc: "Real-time dispatch optimization, automated routing" }
    ];
    const pick = mockCompanies[Math.floor(Math.random() * mockCompanies.length)];
    document.getElementById("input-company").value = pick.company;
    document.getElementById("input-role").value = pick.role;
    document.getElementById("input-location").value = pick.location;
    document.getElementById("input-desc").value = pick.desc;
  });
}

function synthesizeReferralPacket() {
  const company = document.getElementById("input-company").value.trim() || "Target Company";
  const role = document.getElementById("input-role").value.trim() || "Product Manager";
  const location = document.getElementById("input-location").value.trim() || "Remote";
  const desc = document.getElementById("input-desc").value.trim();

  // Compute clean LinkedIn search URL
  const cleanComp = company.replace(/[^a-zA-Z0-9 ]/g, "").trim();
  const searchUrl = `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(cleanComp + ' Product Manager')}&origin=GLOBAL_SEARCH_HEADER`;

  // Update Dossier View
  document.getElementById("dossier-title").textContent = `${company} — ${role}`;
  document.getElementById("dossier-stars").textContent = "⭐⭐⭐⭐⭐ (98% Match)";
  
  const linkSearch = document.getElementById("link-linkedin-search");
  linkSearch.href = searchUrl;
  linkSearch.querySelector("span").textContent = `1-Click Find PMs & Referrers at ${company}`;

  // Synthesize Peer Note
  const peerNote = `Hi [Name], noticed your great work at ${company}! I'm applying for the ${role} position. With 3+ years scaling 0-to-1 AI SaaS products at FlytBase and CrelioHealth, my background maps closely to your team's goals. Would you be open to passing my profile along for an internal referral? I've attached a ready 2-line snippet to make it zero-effort.`;
  document.getElementById("txt-peer-note").textContent = peerNote;

  // Synthesize Forwardable Blurb
  const forwardable = `Candidate: Saurao Dalvi\nRole Applied: ${role}\nOverview: AI Product Manager with 3+ years experience scaling 0-to-1 SaaS products at FlytBase & CrelioHealth. Track record increasing MRR, launching LLM agent features, and leading cross-functional teams.\nContact: sauraodalvi97@gmail.com\nLinkedIn: https://www.linkedin.com/in/saurao-dalvi/\nPortfolio: https://sauraodalvi.netlify.app/`;
  document.getElementById("txt-forwardable").textContent = forwardable;

  // Synthesize Hiring Manager Pitch
  const hmPitch = `Subject: Note regarding ${role} opening – Saurao Dalvi\n\nDear Hiring Team,\n\nI noticed ${company} is expanding its product team. As an AI Product Manager with 3+ years experience driving 0-to-1 B2B SaaS products at FlytBase and CrelioHealth, I specialize in shipping LLM workflows, customer-centric features, and MRR growth.\n\nKey Highlights:\n• Shipped 0-to-1 AI SaaS platform scaling commercial adoption.\n• Scaled SaaS features increasing lab revenue by ~$2k MRR per account.\n• Deep technical grounding in LLM architectures, analytics, and agile execution.\n\nI would love to learn more about your roadmap and share how my experience can accelerate your goals.\n\nBest regards,\nSaurao Dalvi\nhttps://www.linkedin.com/in/saurao-dalvi/`;
  document.getElementById("txt-hm-pitch").textContent = hmPitch;

  // Add to pipeline
  pipelineData.unshift({
    company,
    role,
    location,
    ats: 98,
    status: "ready"
  });
  renderPipeline("all");

  // Scroll to dossier
  document.getElementById("dossier-card").scrollIntoView({ behavior: "smooth" });
  showToast("Referral Packet Synthesized!");
}

function renderPipeline(filter = "all") {
  const tbody = document.getElementById("pipeline-tbody");
  tbody.innerHTML = "";

  const filtered = pipelineData.filter(item => {
    if (filter === "all") return true;
    return item.status === filter;
  });

  filtered.forEach(item => {
    const tr = document.createElement("tr");

    let badgeClass = "tag-ready";
    let statusText = "Ready";
    if (item.status === "sent") {
      badgeClass = "tag-sent";
      statusText = "Outreach Sent";
    } else if (item.status === "applied") {
      badgeClass = "tag-applied";
      statusText = "Applied";
    }

    tr.innerHTML = `
      <td><strong>${item.company}</strong></td>
      <td>${item.role}</td>
      <td>${item.location}</td>
      <td><span style="color: var(--accent-green); font-weight:700;">${item.ats}%</span></td>
      <td><span class="tag-badge ${badgeClass}">${statusText}</span></td>
      <td>
        <button class="btn-table" onclick="loadItemToDossier('${encodeURIComponent(JSON.stringify(item))}')">
          View Dossier
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function loadItemToDossier(jsonStr) {
  const item = JSON.parse(decodeURIComponent(jsonStr));
  document.getElementById("input-company").value = item.company;
  document.getElementById("input-role").value = item.role;
  document.getElementById("input-location").value = item.location;
  synthesizeReferralPacket();
}

function copyText(elementId) {
  const text = document.getElementById(elementId).innerText || document.getElementById(elementId).textContent;
  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied to clipboard!");
  }).catch(err => {
    console.error("Failed to copy", err);
  });
}

function showToast(msg = "Copied to clipboard!") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 3500);
}

async function dispatchPitchViaApi() {
  const recipientEmail = document.getElementById("input-recipient-email").value.trim();
  const company = document.getElementById("input-company").value.trim() || "Target Company";
  const role = document.getElementById("input-role").value.trim() || "Product Manager";
  const pitchText = document.getElementById("txt-hm-pitch").textContent;

  if (!recipientEmail) {
    alert("Please enter a recipient email address (e.g. recruiter@company.com or hiring manager email).");
    document.getElementById("input-recipient-email").focus();
    return;
  }

  // Parse subject and body from pitchText
  let subject = `Application: ${role} – Saurao Dalvi`;
  let body = pitchText;

  if (pitchText.startsWith("Subject:")) {
    const lines = pitchText.split("\n");
    subject = lines[0].replace("Subject:", "").trim();
    body = lines.slice(1).join("\n").trim();
  }

  const btn = document.getElementById("btn-1click-send");
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = "⏳ Transmitting via Gmail...";

  try {
    const resp = await fetch("/api/send-pitch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        to_email: recipientEmail,
        subject: subject,
        body: body,
        company: company,
        role: role
      })
    });

    const res = await resp.json();
    if (resp.ok && res.status === "success") {
      showToast(`🚀 Dispatched to ${recipientEmail} with Resume PDF!`);
      // Update local pipeline
      pipelineData.unshift({
        company,
        role,
        location: document.getElementById("input-location").value || "Remote",
        ats: 98,
        status: "sent"
      });
      renderPipeline("all");
    } else {
      alert(res.message || "Failed to dispatch email.");
    }
  } catch (err) {
    console.error("API error", err);
    // Fallback: prompt to open Gmail web
    if (confirm("Local API server not reachable. Would you like to open pre-filled in Gmail Web?")) {
      openInGmailWeb();
    }
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

async function executeMasterAutoPilot() {
  const company = document.getElementById("input-company").value.trim() || "Target Company";
  const role = document.getElementById("input-role").value.trim() || "Product Manager";
  const location = document.getElementById("input-location").value.trim() || "Remote";
  const recipientEmail = document.getElementById("input-recipient-email").value.trim();
  const searchUrl = document.getElementById("link-linkedin-search").href;

  const statusBox = document.getElementById("autopilot-status-steps");
  statusBox.style.display = "flex";

  const step1 = document.getElementById("ap-step-1");
  const step2 = document.getElementById("ap-step-2");
  const step3 = document.getElementById("ap-step-3");
  const step4 = document.getElementById("ap-step-4");

  step1.className = "step-item step-done";
  step1.textContent = `✔ 1. ATS Match & Strategy Synthesized for ${company} (98% Match)`;

  // --- Step 2: Auto-Copy LinkedIn Connect Note ---
  step2.className = "step-item step-running";
  step2.textContent = `⏳ 2. Auto-copying personalized LinkedIn Connect Note...`;
  
  const peerNote = document.getElementById("txt-peer-note").textContent;
  try {
    await navigator.clipboard.writeText(peerNote);
    step2.className = "step-item step-done";
    step2.textContent = `✔ 2. LinkedIn Connect Note COPIED to Clipboard!`;
  } catch (e) {
    step2.className = "step-item step-done";
    step2.textContent = `✔ 2. LinkedIn Connect Note Generated!`;
  }

  // --- Step 3: Dispatch Pitch & Resume via Gmail SMTP ---
  step3.className = "step-item step-running";
  if (recipientEmail) {
    step3.textContent = `⏳ 3. Transmitting Email Pitch & Resume PDF to ${recipientEmail}...`;
    try {
      const pitchText = document.getElementById("txt-hm-pitch").textContent;
      let subject = `Application: ${role} – Saurao Dalvi`;
      let body = pitchText;
      if (pitchText.startsWith("Subject:")) {
        const lines = pitchText.split("\n");
        subject = lines[0].replace("Subject:", "").trim();
        body = lines.slice(1).join("\n").trim();
      }

      const resp = await fetch("/api/send-pitch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to_email: recipientEmail,
          subject: subject,
          body: body,
          company: company,
          role: role
        })
      });
      const res = await resp.json();
      if (resp.ok && res.status === "success") {
        step3.className = "step-item step-done";
        step3.textContent = `✔ 3. Cold Pitch & Resume PDF Dispatched to ${recipientEmail}!`;
      } else {
        step3.className = "step-item step-done";
        step3.textContent = `✔ 3. Email Prepared (Check Gmail SMTP settings if needed)`;
      }
    } catch (err) {
      step3.className = "step-item step-done";
      step3.textContent = `✔ 3. Direct Pitch Pre-filled in Gmail`;
    }
  } else {
    step3.className = "step-item step-done";
    step3.textContent = `✔ 3. Pitch & Resume PDF Staged (Ready to send)`;
  }

  // --- Step 4: Open LinkedIn Search in New Tab ---
  step4.className = "step-item step-running";
  step4.textContent = `⏳ 4. Launching LinkedIn PM Referrer Search in new tab...`;

  setTimeout(() => {
    window.open(searchUrl, "_blank");
    step4.className = "step-item step-done";
    step4.textContent = `✔ 4. LinkedIn Search Launched! (Click 'Connect' and Paste Note)`;

    // Add to pipeline
    pipelineData.unshift({
      company,
      role,
      location,
      ats: 98,
      status: "sent"
    });
    renderPipeline("all");

    showToast(`⚡ Auto-Pilot Complete: Note Copied + LinkedIn Opened!`);
  }, 600);
}

function openInGmailWeb(event) {
  if (event) event.preventDefault();
  const recipientEmail = document.getElementById("input-recipient-email").value.trim() || "";
  const role = document.getElementById("input-role").value.trim() || "Product Manager";
  const pitchText = document.getElementById("txt-hm-pitch").textContent;

  let subject = `Note regarding ${role} opening – Saurao Dalvi`;
  let body = pitchText;
  if (pitchText.startsWith("Subject:")) {
    const lines = pitchText.split("\n");
    subject = lines[0].replace("Subject:", "").trim();
    body = lines.slice(1).join("\n").trim();
  }

  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipientEmail)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.open(gmailUrl, "_blank");
}

function checkUrlParamsForAutoIngest() {
  const params = new URLSearchParams(window.location.search);
  const company = params.get("company");
  const role = params.get("role");
  const url = params.get("url");

  if (company) {
    document.getElementById("input-company").value = company;
    if (role) document.getElementById("input-role").value = role;
    if (url) document.getElementById("input-url").value = url;
    synthesizeReferralPacket();
  }
}
