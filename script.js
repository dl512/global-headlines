// Sample data structure - replace with your actual data
// You can either fetch from Google Sheets API or update this manually
const headlinesData = [
  {
    country: "British",
    newspaper: "The Sunday Times",
    website: "https://www.thetimes.com/",
    headline:
      "Diane Keaton obituary: Oscar winner who redefined the independent woman",
    link: "https://www.thetimes.com/uk/obituaries/article/diane-keaton-obituary-death-60sh503dg",
    flag: "🇬🇧",
  },
  {
    country: "Qatar",
    newspaper: "Doha News",
    website: "https://dohanews.co/",
    headline: "",
    link: "",
    flag: "🇶🇦",
  },
  {
    country: "Georgia",
    newspaper: "Civil Georgia",
    website: "https://civil.ge/",
    headline: "",
    link: "",
    flag: "🇬🇪",
  },
  {
    country: "The Philippines",
    newspaper: "Philippine Daily Inquirer",
    website: "https://www.inquirer.net/",
    headline: "",
    link: "",
    flag: "🇵🇭",
  },
  {
    country: "Puerto Rico",
    newspaper: "NotiCel",
    website: "https://noticel.com/",
    headline: "",
    link: "",
    flag: "🇵🇷",
  },
  {
    country: "Jordan",
    newspaper: "The Jordan Times",
    website: "https://jordantimes.com/",
    headline: "",
    link: "",
    flag: "🇯🇴",
  },
  {
    country: "Ireland",
    newspaper: "The Irish Times",
    website: "https://www.irishtimes.com/",
    headline: "",
    link: "",
    flag: "🇮🇪",
  },
  {
    country: "Australia",
    newspaper: "The Sydney Morning Herald",
    website: "https://www.smh.com.au/",
    headline: "",
    link: "",
    flag: "🇦🇺",
  },
  {
    country: "Sweden",
    newspaper: "Sveriges Television (SVT)",
    website: "https://www.svt.se/",
    headline: "",
    link: "",
    flag: "🇸🇪",
  },
  {
    country: "Tunisia",
    newspaper: "Nawaat",
    website: "https://nawaat.org/",
    headline: "",
    link: "",
    flag: "🇹🇳",
  },
  {
    country: "Albania",
    newspaper: "Tirana Times",
    website: "https://www.tiranatimes.com/",
    headline: "",
    link: "",
    flag: "🇦🇱",
  },
];

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
            <div class="country-info">
                <div class="country-name">${data.country}</div>
                <div class="newspaper-name">
                    <a href="${
                      data.website
                    }" target="_blank" rel="noopener noreferrer" class="newspaper-link">
                        ${data.newspaper}
                    </a>
                </div>
            </div>
            <div class="flag-icon">${data.flag || getFlag(data.country)}</div>
        </div>
        <div class="headline-content">
            ${
              hasHeadline
                ? `
                <p class="headline-text">${data.headline}</p>
            `
                : `
                <p class="headline-text no-headline-text">No headline available yet</p>
            `
            }
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
  // TODO: Add your Google Sheets API key here
  // IMPORTANT: Use a restricted API key for public websites
  // Get your API key from: https://console.cloud.google.com/apis/credentials
  // Make sure to restrict it to Google Sheets API and your domain
  const API_KEY = "YOUR_API_KEY_HERE"; // Replace with your API key
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
