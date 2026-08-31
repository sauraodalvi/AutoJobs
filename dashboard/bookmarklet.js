// AutoJobs 1-Click Browser Bookmarklet
// Drag this script or save it as a bookmark in Chrome/Brave/Edge/Firefox.
// When you're on LinkedIn Jobs, Greenhouse, Lever, or any company career page,
// click this bookmark to automatically extract the company and job title,
// and open your AutoJobs Referral AI Agent dashboard with pre-filled referral packets.

javascript:(function(){
  let company = "";
  let role = "";
  const pageTitle = document.title || "";
  const pageUrl = window.location.href;

  // 1. LinkedIn Jobs Parsing
  if (pageUrl.includes("linkedin.com/jobs")) {
    const compEl = document.querySelector(".job-details-jobs-unified-top-card__company-name") || document.querySelector(".jobs-unified-top-card__company-name");
    const roleEl = document.querySelector(".job-details-jobs-unified-top-card__job-title") || document.querySelector(".jobs-unified-top-card__job-title");
    if (compEl) company = compEl.innerText.trim();
    if (roleEl) role = roleEl.innerText.trim();
  }

  // 2. Greenhouse / Lever / Workday / Generic Fallback
  if (!company) {
    if (pageTitle.includes("hiring")) {
      const parts = pageTitle.split(" hiring ");
      role = parts[0].trim();
      company = parts[1].split("|")[0].split("-")[0].trim();
    } else if (pageTitle.includes(" - ")) {
      const parts = pageTitle.split(" - ");
      role = parts[0].trim();
      company = parts[1].trim();
    } else if (pageTitle.includes(" at ")) {
      const parts = pageTitle.split(" at ");
      role = parts[0].trim();
      company = parts[1].split("|")[0].trim();
    }
  }

  company = company || prompt("Target Company Name:", "");
  role = role || prompt("Target Role Title:", "Product Manager");

  if (company) {
    const targetDashboard = "http://localhost:8000/dashboard/";
    const finalUrl = targetDashboard + "?company=" + encodeURIComponent(company) + "&role=" + encodeURIComponent(role) + "&url=" + encodeURIComponent(pageUrl);
    window.open(finalUrl, "_blank");
  }
})();
