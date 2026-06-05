// Vercel Serverless Function — fetches & parses HLB forex rates
// Endpoint: GET /api/rates

const HLB_URL = 'https://www.hlb.com.my/en/global-markets/forex-rates.html';

const HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
  Accept:
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
  Referer: 'https://www.hlb.com.my/',
};

function extractNumber(text) {
  const m = text.match(/\d+\.\d+/g);
  return m ? parseFloat(m[m.length - 1]) : null;
}

function parseRates(html) {
  // Match table rows via regex (no DOM in Node by default)
  const rates = {};
  let unit = 1;

  // Find the forex-rates-table content
  const tableMatch = html.match(/<table[^>]*forex-rates-table[^>]*>([\s\S]*?)<\/table>/i);
  if (!tableMatch) return rates;

  const tableHtml = tableMatch[1];
  const rowRegex = /<tr[^>]*>([\s\S]*?)<\/tr>/gi;
  let rowMatch;

  while ((rowMatch = rowRegex.exec(tableHtml)) !== null) {
    const rowHtml = rowMatch[1];
    // Extract all td/th cell texts
    const cells = [];
    const cellRegex = /<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi;
    let cellMatch;
    while ((cellMatch = cellRegex.exec(rowHtml)) !== null) {
      // Strip inner HTML tags to get text
      const text = cellMatch[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      cells.push(text);
    }
    if (cells.length < 2) continue;

    const label = cells[1] || '';
    if (label.includes('100 UNITS')) unit = 100;
    else if (label.includes('1 UNIT') && !label.includes('100')) unit = 1;

    const codeMatch = label.match(/\(([A-Z]{3})\)/);
    if (!codeMatch) continue;
    const code = codeMatch[1];

    const sell = cells[2] ? extractNumber(cells[2]) : null;
    const buy  = cells[3] ? extractNumber(cells[3]) : null;

    rates[code] = { sell, buy, unit };
  }

  return rates;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');

  try {
    const response = await fetch(HLB_URL, { headers: HEADERS });
    if (!response.ok) throw new Error(`HLB returned ${response.status}`);

    const html  = await response.text();
    const rates = parseRates(html);
    const count = Object.keys(rates).length;

    if (count === 0) throw new Error('No rates parsed — page structure may have changed');

    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=60');
    res.status(200).json({ rates, count, fetchedAt: new Date().toISOString() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
