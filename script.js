// Data will be fetched from Google Sheets
let headlinesData = [];

// Country to flag emoji mapping
const countryFlags = {
  British: "🇬🇧",
  "United Kingdom": "🇬🇧",
  UK: "🇬🇧",
  Qatar: "🇶🇦",
  Georgia: "🇬🇪",
  "The Philippines": "🇵🇭",
  Philippines: "🇵🇭",
  "Puerto Rico": "🇵🇷",
  Jordan: "🇯🇴",
  Ireland: "🇮🇪",
  Australia: "🇦🇺",
  Sweden: "🇸🇪",
  Tunisia: "🇹🇳",
  Albania: "🇦🇱",
  "United States": "🇺🇸",
  USA: "🇺🇸",
  Canada: "🇨🇦",
  France: "🇫🇷",
  Germany: "🇩🇪",
  Italy: "🇮🇹",
  Spain: "🇪🇸",
  Japan: "🇯🇵",
  China: "🇨🇳",
  India: "🇮🇳",
  Brazil: "🇧🇷",
  Mexico: "🇲🇽",
  Russia: "🇷🇺",
  "South Korea": "🇰🇷",
  Netherlands: "🇳🇱",
  Belgium: "🇧🇪",
  Switzerland: "🇨🇭",
  Austria: "🇦🇹",
  Poland: "🇵🇱",
  Turkey: "🇹🇷",
  Egypt: "🇪🇬",
  "South Africa": "🇿🇦",
  Nigeria: "🇳🇬",
  Kenya: "🇰🇪",
  Argentina: "🇦🇷",
  Chile: "🇨🇱",
  Colombia: "🇨🇴",
  Peru: "🇵🇪",
  Thailand: "🇹🇭",
  Vietnam: "🇻🇳",
  Indonesia: "🇮🇩",
  Malaysia: "🇲🇾",
  Singapore: "🇸🇬",
  "New Zealand": "🇳🇿",
  Norway: "🇳🇴",
  Denmark: "🇩🇰",
  Finland: "🇫🇮",
  Portugal: "🇵🇹",
  Greece: "🇬🇷",
  "Czech Republic": "🇨🇿",
  Hungary: "🇭🇺",
  Romania: "🇷🇴",
  Ukraine: "🇺🇦",
  Israel: "🇮🇱",
  UAE: "🇦🇪",
  "Saudi Arabia": "🇸🇦",
  Pakistan: "🇵🇰",
  Bangladesh: "🇧🇩",
};

// Get flag for country
function getFlag(country) {
  return countryFlags[country] || "🌍";
}

// Format date
function formatDate(date) {
  const options = {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  };
  return date.toLocaleDateString("en-US", options);
}

// Create headline card
function createHeadlineCard(data) {
  const hasHeadline = data.headline && data.headline.trim() !== "";

  const card = document.createElement("div");
  card.className = `headline-card ${!hasHeadline ? "no-headline" : ""}`;
  card.dataset.country = data.country.toLowerCase();
  card.dataset.newspaper = data.newspaper.toLowerCase();

  card.innerHTML = `
        <div class="card-header">
            <div class="country-name">${data.country}</div>
            <div class="flag-icon">${data.flag || getFlag(data.country)}</div>
        </div>
        <div class="headline-content">
            ${
              hasHeadline
                ? `
                <h3 class="headline-text">${data.headline}</h3>
            `
                : `
                <h3 class="headline-text no-headline-text">No headline available yet</h3>
            `
            }
            <p class="newspaper-name">${data.newspaper}</p>
        </div>
        ${
          hasHeadline && data.link
            ? `
            <a href="${data.link}" target="_blank" rel="noopener noreferrer" class="read-more">
                Read full story
            </a>
        `
            : ""
        }
    `;

  return card;
}

// Render headlines
function renderHeadlines(data) {
  const container = document.getElementById("headlinesContainer");
  const loadingState = document.getElementById("loadingState");

  loadingState.style.display = "none";
  container.innerHTML = "";

  if (data.length === 0) {
    container.innerHTML = `
            <div class="empty-state">
                <p>No headlines found matching your search.</p>
            </div>
        `;
    return;
  }

  data.forEach((item) => {
    const card = createHeadlineCard(item);
    container.appendChild(card);
  });
}

// Search functionality
function setupSearch() {
  const searchInput = document.getElementById("searchInput");

  searchInput.addEventListener("input", (e) => {
    const searchTerm = e.target.value.toLowerCase();

    const filteredData = headlinesData.filter((item) => {
      return (
        item.country.toLowerCase().includes(searchTerm) ||
        item.newspaper.toLowerCase().includes(searchTerm)
      );
    });

    renderHeadlines(filteredData);
  });
}

// Initialize the app
function init() {
  // Update last updated time
  const updateTimeElement = document.getElementById("updateTime");
  updateTimeElement.textContent = formatDate(new Date());

  // Render headlines
  renderHeadlines(headlinesData);

  // Setup search
  setupSearch();
}

// Fetch data from Google Sheets
async function fetchFromGoogleSheets() {
  const SHEET_ID = "1oHKGMuBynXOJkkQpDTAtjfsv-jrTXpzI2jj29VCCDaM";
  const API_KEY = "AIzaSyCPyerGljBK4JJ-XA3aRr5cRvWssI3rwhI";
  const SHEET_NAME = "Sheet1";
  const RANGE = `${SHEET_NAME}!A2:F`; // Start from row 2 to skip header

  const sheetLink = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${RANGE}?key=${API_KEY}`;

  try {
    console.log("Fetching data from Google Sheets...");
    const response = await fetch(sheetLink);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log("Data fetched successfully:", data);

    // Check if we got any values
    if (!data.values || data.values.length === 0) {
      console.warn("No data found in sheet");
      return [];
    }

    // Map the rows to headline objects
    const headlines = data.values
      .filter((row) => row[0] && row[1]) // Only include rows with country and newspaper
      .map((row) => ({
        country: row[0] || "",
        newspaper: row[1] || "",
        website: row[2] || "",
        headline: row[4] || "", // Column E (index 4)
        link: row[5] || "", // Column F (index 5)
        flag: getFlag(row[0] || ""),
      }));

    console.log(`Loaded ${headlines.length} headlines from Google Sheets`);
    return headlines;
  } catch (error) {
    console.error("Error fetching data from Google Sheets:", error);
    document.getElementById("errorState").style.display = "block";
    document.getElementById("loadingState").style.display = "none";
    return [];
  }
}

// Initialize with external data
async function initApp() {
  // Load from Google Sheets (live data)
  const googleSheetsData = await fetchFromGoogleSheets();
  if (googleSheetsData && googleSheetsData.length > 0) {
    headlinesData.splice(0, headlinesData.length, ...googleSheetsData);
    console.log("Using live data from Google Sheets");
  } else {
    console.log("Using embedded sample data");
  }

  init();
}

// Run when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}
