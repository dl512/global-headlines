// Data will be fetched from Google Sheets
let headlinesData = [];

// Country to flag emoji mapping - All UN recognized countries
const countryFlags = {
  // A
  Afghanistan: "🇦🇫",
  Albania: "🇦🇱",
  Algeria: "🇩🇿",
  Andorra: "🇦🇩",
  Angola: "🇦🇴",
  "Antigua and Barbuda": "🇦🇬",
  Argentina: "🇦🇷",
  Armenia: "🇦🇲",
  Australia: "🇦🇺",
  Austria: "🇦🇹",
  Azerbaijan: "🇦🇿",

  // B
  Bahamas: "🇧🇸",
  "The Bahamas": "🇧🇸",
  Bahrain: "🇧🇭",
  Bangladesh: "🇧🇩",
  Barbados: "🇧🇧",
  Belarus: "🇧🇾",
  Belgium: "🇧🇪",
  Belize: "🇧🇿",
  Benin: "🇧🇯",
  Bhutan: "🇧🇹",
  Bolivia: "🇧🇴",
  "Bosnia and Herzegovina": "🇧🇦",
  Botswana: "🇧🇼",
  Brazil: "🇧🇷",
  Brunei: "🇧🇳",
  Bulgaria: "🇧🇬",
  "Burkina Faso": "🇧🇫",
  Burundi: "🇧🇮",

  // C
  "Cabo Verde": "🇨🇻",
  "Cape Verde": "🇨🇻",
  Cambodia: "🇰🇭",
  Cameroon: "🇨🇲",
  Canada: "🇨🇦",
  "Central African Republic": "🇨🇫",
  Chad: "🇹🇩",
  Chile: "🇨🇱",
  China: "🇨🇳",
  Colombia: "🇨🇴",
  Comoros: "🇰🇲",
  Congo: "🇨🇬",
  "Republic of the Congo": "🇨🇬",
  "Democratic Republic of the Congo": "🇨🇩",
  "DR Congo": "🇨🇩",
  "Costa Rica": "🇨🇷",
  Croatia: "🇭🇷",
  Cuba: "🇨🇺",
  Cyprus: "🇨🇾",
  Czechia: "🇨🇿",
  "Czech Republic": "🇨🇿",

  // D
  Denmark: "🇩🇰",
  Djibouti: "🇩🇯",
  Dominica: "🇩🇲",
  "Dominican Republic": "🇩🇴",

  // E
  Ecuador: "🇪🇨",
  Egypt: "🇪🇬",
  "El Salvador": "🇸🇻",
  "Equatorial Guinea": "🇬🇶",
  Eritrea: "🇪🇷",
  Estonia: "🇪🇪",
  Eswatini: "🇸🇿",
  Swaziland: "🇸🇿",
  Ethiopia: "🇪🇹",

  // F
  Fiji: "🇫🇯",
  Finland: "🇫🇮",
  France: "🇫🇷",

  // G
  Gabon: "🇬🇦",
  Gambia: "🇬🇲",
  "The Gambia": "🇬🇲",
  Georgia: "🇬🇪",
  Germany: "🇩🇪",
  Ghana: "🇬🇭",
  Greece: "🇬🇷",
  Grenada: "🇬🇩",
  Guatemala: "🇬🇹",
  Guinea: "🇬🇳",
  "Guinea-Bissau": "🇬🇼",
  Guyana: "🇬🇾",

  // H
  Haiti: "🇭🇹",
  Honduras: "🇭🇳",
  Hungary: "🇭🇺",

  // I
  Iceland: "🇮🇸",
  India: "🇮🇳",
  Indonesia: "🇮🇩",
  Iran: "🇮🇷",
  Iraq: "🇮🇶",
  Ireland: "🇮🇪",
  Israel: "🇮🇱",
  Italy: "🇮🇹",
  "Ivory Coast": "🇨🇮",
  "Côte d'Ivoire": "🇨🇮",

  // J
  Jamaica: "🇯🇲",
  Japan: "🇯🇵",
  Jordan: "🇯🇴",

  // K
  Kazakhstan: "🇰🇿",
  Kenya: "🇰🇪",
  Kiribati: "🇰🇮",
  Kuwait: "🇰🇼",
  Kyrgyzstan: "🇰🇬",

  // L
  Laos: "🇱🇦",
  Latvia: "🇱🇻",
  Lebanon: "🇱🇧",
  Lesotho: "🇱🇸",
  Liberia: "🇱🇷",
  Libya: "🇱🇾",
  Liechtenstein: "🇱🇮",
  Lithuania: "🇱🇹",
  Luxembourg: "🇱🇺",

  // M
  Madagascar: "🇲🇬",
  Malawi: "🇲🇼",
  Malaysia: "🇲🇾",
  Maldives: "🇲🇻",
  Mali: "🇲🇱",
  Malta: "🇲🇹",
  "Marshall Islands": "🇲🇭",
  Mauritania: "🇲🇷",
  Mauritius: "🇲🇺",
  Mexico: "🇲🇽",
  Micronesia: "🇫🇲",
  Moldova: "🇲🇩",
  Monaco: "🇲🇨",
  Mongolia: "🇲🇳",
  Montenegro: "🇲🇪",
  Morocco: "🇲🇦",
  Mozambique: "🇲🇿",
  Myanmar: "🇲🇲",
  Burma: "🇲🇲",

  // N
  Namibia: "🇳🇦",
  Nauru: "🇳🇷",
  Nepal: "🇳🇵",
  Netherlands: "🇳🇱",
  "New Zealand": "🇳🇿",
  Nicaragua: "🇳🇮",
  Niger: "🇳🇪",
  Nigeria: "🇳🇬",
  "North Korea": "🇰🇵",
  "North Macedonia": "🇲🇰",
  Macedonia: "🇲🇰",
  Norway: "🇳🇴",

  // O
  Oman: "🇴🇲",

  // P
  Pakistan: "🇵🇰",
  Palau: "🇵🇼",
  Palestine: "🇵🇸",
  Panama: "🇵🇦",
  "Papua New Guinea": "🇵🇬",
  Paraguay: "🇵🇾",
  Peru: "🇵🇪",
  Philippines: "🇵🇭",
  "The Philippines": "🇵🇭",
  Poland: "🇵🇱",
  Portugal: "🇵🇹",
  "Puerto Rico": "🇵🇷",

  // Q
  Qatar: "🇶🇦",

  // R
  Romania: "🇷🇴",
  Russia: "🇷🇺",
  "Russian Federation": "🇷🇺",
  Rwanda: "🇷🇼",

  // S
  "Saint Kitts and Nevis": "🇰🇳",
  "Saint Lucia": "🇱🇨",
  "Saint Vincent and the Grenadines": "🇻🇨",
  Samoa: "🇼🇸",
  "San Marino": "🇸🇲",
  "Sao Tome and Principe": "🇸🇹",
  "Saudi Arabia": "🇸🇦",
  Senegal: "🇸🇳",
  Serbia: "🇷🇸",
  Seychelles: "🇸🇨",
  "Sierra Leone": "🇸🇱",
  Singapore: "🇸🇬",
  Slovakia: "🇸🇰",
  Slovenia: "🇸🇮",
  "Solomon Islands": "🇸🇧",
  Somalia: "🇸🇴",
  "South Africa": "🇿🇦",
  "South Korea": "🇰🇷",
  Korea: "🇰🇷",
  "South Sudan": "🇸🇸",
  Spain: "🇪🇸",
  "Sri Lanka": "🇱🇰",
  Sudan: "🇸🇩",
  Suriname: "🇸🇷",
  Sweden: "🇸🇪",
  Switzerland: "🇨🇭",
  Syria: "🇸🇾",

  // T
  Tajikistan: "🇹🇯",
  Tanzania: "🇹🇿",
  Thailand: "🇹🇭",
  "Timor-Leste": "🇹🇱",
  "East Timor": "🇹🇱",
  Togo: "🇹🇬",
  Tonga: "🇹🇴",
  "Trinidad and Tobago": "🇹🇹",
  Tunisia: "🇹🇳",
  Turkey: "🇹🇷",
  Türkiye: "🇹🇷",
  Turkmenistan: "🇹🇲",
  Tuvalu: "🇹🇻",

  // U
  Uganda: "🇺🇬",
  Ukraine: "🇺🇦",
  "United Arab Emirates": "🇦🇪",
  UAE: "🇦🇪",
  "United Kingdom": "🇬🇧",
  UK: "🇬🇧",
  Britain: "🇬🇧",
  British: "🇬🇧",
  "United States": "🇺🇸",
  "United States of America": "🇺🇸",
  USA: "🇺🇸",
  US: "🇺🇸",
  America: "🇺🇸",
  Uruguay: "🇺🇾",
  Uzbekistan: "🇺🇿",

  // V
  Vanuatu: "🇻🇺",
  "Vatican City": "🇻🇦",
  Vatican: "🇻🇦",
  Venezuela: "🇻🇪",
  Vietnam: "🇻🇳",
  "Viet Nam": "🇻🇳",

  // Y
  Yemen: "🇾🇪",

  // Z
  Zambia: "🇿🇲",
  Zimbabwe: "🇿🇼",
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

  // Filter to only show items with headlines
  const dataWithHeadlines = data.filter(
    (item) => item.headline && item.headline.trim() !== ""
  );

  if (dataWithHeadlines.length === 0) {
    container.innerHTML = `
            <div class="empty-state">
                <p>No headlines found matching your search.</p>
            </div>
        `;
    return;
  }

  dataWithHeadlines.forEach((item) => {
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
