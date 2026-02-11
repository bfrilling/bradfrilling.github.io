const analyzeBtn = document.getElementById('analyzeBtn');
const tickersInput = document.getElementById('tickers');
const tableBody = document.querySelector('#resultsTable tbody');

analyzeBtn.addEventListener('click', async () => {
  const tickers = tickersInput.value
    .split(',')
    .map((ticker) => ticker.trim().toUpperCase())
    .filter(Boolean);

  if (tickers.length === 0) {
    renderMessageRow('Please enter at least one ticker.');
    return;
  }

  renderMessageRow('Loading and calculating indicators...');

  const results = [];
  for (const ticker of tickers) {
    try {
      const candles = await fetchIntradayCandles(ticker);
      const metrics = computeIndicators(candles);
      const scored = scoreTicker(ticker, metrics);
      results.push(scored);
    } catch (error) {
      console.warn(`Skipping ${ticker}:`, error.message);
    }
  }

  if (results.length === 0) {
    renderMessageRow('No valid ticker data was returned. Try different symbols.');
    return;
  }

  results.sort((a, b) => b.score - a.score);
  renderResults(results);
});

function renderMessageRow(message) {
  tableBody.innerHTML = `<tr><td colspan="8">${message}</td></tr>`;
}

function renderResults(results) {
  tableBody.innerHTML = '';

  for (const result of results) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${result.ticker}</td>
      <td>${result.score}</td>
      <td class="${result.signalClass}">${result.signal}</td>
      <td>${result.price.toFixed(2)}</td>
      <td>${result.rsi.toFixed(1)}</td>
      <td>${result.macd.toFixed(3)} / ${result.macdSignal.toFixed(3)}</td>
      <td>${result.emaShort.toFixed(2)} / ${result.emaLong.toFixed(2)}</td>
      <td>${result.vwap.toFixed(2)}</td>
    `;
    tableBody.appendChild(row);
  }
}

async function fetchIntradayCandles(ticker) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=5m&range=1d`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const data = await response.json();
  const quote = data?.chart?.result?.[0]?.indicators?.quote?.[0];
  if (!quote?.close || !quote?.high || !quote?.low || !quote?.volume) {
    throw new Error('Missing candle data');
  }

  const closes = quote.close.filter((v) => typeof v === 'number');
  const highs = quote.high.filter((v) => typeof v === 'number');
  const lows = quote.low.filter((v) => typeof v === 'number');
  const volumes = quote.volume.filter((v) => typeof v === 'number');

  const length = Math.min(closes.length, highs.length, lows.length, volumes.length);
  if (length < 30) {
    throw new Error('Not enough candles');
  }

  return {
    closes: closes.slice(-length),
    highs: highs.slice(-length),
    lows: lows.slice(-length),
    volumes: volumes.slice(-length),
  };
}

function computeIndicators({ closes, highs, lows, volumes }) {
  const emaShortSeries = ema(closes, 9);
  const emaLongSeries = ema(closes, 21);

  const { macdSeries, signalSeries } = macd(closes, 12, 26, 9);
  const rsiValue = rsi(closes, 14);
  const vwapValue = vwap(highs, lows, closes, volumes);

  return {
    price: closes[closes.length - 1],
    emaShort: emaShortSeries[emaShortSeries.length - 1],
    emaLong: emaLongSeries[emaLongSeries.length - 1],
    macd: macdSeries[macdSeries.length - 1],
    macdSignal: signalSeries[signalSeries.length - 1],
    rsi: rsiValue,
    vwap: vwapValue,
  };
}

function scoreTicker(ticker, metrics) {
  let score = 0;

  if (metrics.rsi >= 45 && metrics.rsi <= 65) score += 25;
  if (metrics.macd > metrics.macdSignal) score += 30;
  if (metrics.emaShort > metrics.emaLong) score += 25;
  if (metrics.price > metrics.vwap) score += 20;

  let signal = 'Avoid';
  let signalClass = 'avoid';

  if (score >= 75) {
    signal = 'Buy Candidate';
    signalClass = 'buy';
  } else if (score >= 45) {
    signal = 'Watch';
    signalClass = 'watch';
  }

  return { ticker, score, signal, signalClass, ...metrics };
}

function ema(values, period) {
  const k = 2 / (period + 1);
  const result = [values[0]];
  for (let i = 1; i < values.length; i += 1) {
    result.push(values[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}

function macd(values, shortPeriod, longPeriod, signalPeriod) {
  const shortEma = ema(values, shortPeriod);
  const longEma = ema(values, longPeriod);

  const macdSeries = values.map((_, i) => shortEma[i] - longEma[i]);
  const signalSeries = ema(macdSeries, signalPeriod);
  return { macdSeries, signalSeries };
}

function rsi(values, period) {
  let gainSum = 0;
  let lossSum = 0;

  for (let i = 1; i <= period; i += 1) {
    const diff = values[i] - values[i - 1];
    if (diff >= 0) gainSum += diff;
    else lossSum += Math.abs(diff);
  }

  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;

  for (let i = period + 1; i < values.length; i += 1) {
    const diff = values[i] - values[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? Math.abs(diff) : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
  }

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

function vwap(highs, lows, closes, volumes) {
  let cumulativePriceVolume = 0;
  let cumulativeVolume = 0;

  for (let i = 0; i < closes.length; i += 1) {
    const typicalPrice = (highs[i] + lows[i] + closes[i]) / 3;
    cumulativePriceVolume += typicalPrice * volumes[i];
    cumulativeVolume += volumes[i];
  }

  return cumulativeVolume === 0 ? closes[closes.length - 1] : cumulativePriceVolume / cumulativeVolume;
}
