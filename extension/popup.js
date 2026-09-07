document.addEventListener("DOMContentLoaded", async () => {
  const output = document.getElementById("output");
  const copyBtn = document.getElementById("copyBtn");
  const statusArea = document.getElementById("status_area");
  const successContainer = document.getElementById("success_container");
  const loginContainer = document.getElementById("login_container");
  const loginBtn = document.getElementById("loginBtn");
  
  try {
    // Fetch cookies for .espn.com
    const cookies = await chrome.cookies.getAll({ domain: ".espn.com" });
    let swid = cookies.find(c => c.name === "SWID")?.value;
    let espn_s2 = cookies.find(c => c.name === "espn_s2")?.value;
    
    // Sometimes SWID exists but espn_s2 drops if the session expires
    if (!espn_s2 || !swid) {
      statusArea.innerHTML = "<span style='color:#c62828;'>Could not find cookies. Please log into ESPN first.</span>";
      loginContainer.classList.remove("hidden");
      successContainer.classList.add("hidden");
    } else {
      // Ensure SWID is wrapped in {brackets}
      const cleanSwid = swid.replace(/[{}]/g, '');
      let outputText = `SWID="{${cleanSwid}}"\nESPN_S2="${espn_s2}"`;
      
      // Check current tab for leagueId and teamId
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs.length > 0 && tabs[0].url) {
        try {
          const url = new URL(tabs[0].url);
          const leagueId = url.searchParams.get("leagueId");
          const teamId = url.searchParams.get("teamId");
          
          if (leagueId && teamId) {
            outputText = `LEAGUE_ID="${leagueId}"\nTEAM_ID="${teamId}"\n` + outputText;
            statusArea.innerHTML = "<span style='color:#2e7d32;'>Cookies, League ID, and Team ID extracted!</span>";
          } else {
            statusArea.innerHTML = "<span style='color:#2e7d32;'>Cookies extracted!</span><br><span style='color:#1565c0; font-size:12px;'>Navigate to your team page to also get League & Team ID.</span>";
          }
        } catch (e) {
          statusArea.innerHTML = "<span style='color:#2e7d32;'>Cookies extracted!</span>";
        }
      }
      
      output.value = outputText;
      successContainer.classList.remove("hidden");
      loginContainer.classList.add("hidden");
    }
  } catch (err) {
    statusArea.innerHTML = `<span style='color:#c62828;'>Error reading cookies: ${err.message}</span>`;
  }
  
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(output.value);
    copyBtn.innerText = "Copied!";
    setTimeout(() => { copyBtn.innerText = "Copy to Clipboard"; }, 2000);
  });

  loginBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: "https://www.espn.com/fantasy/" });
  });
});
