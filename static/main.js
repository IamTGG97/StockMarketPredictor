const form = document.getElementById('stockForm');
const result = document.getElementById('result');
let chart;

form.addEventListener('submit', async (event) => {
	event.preventDefault();
	result.innerHTML = '<p class="status">Loading market data...</p>';

	const params = new URLSearchParams({
		symbol: document.getElementById('stockSymbol').value.trim().toUpperCase(),
		start_date: document.getElementById('startDate').value,
		end_date: document.getElementById('endDate').value,
		forecast_days: document.getElementById('forecastDays').value
	});

	try {
		const response = await fetch(`/api/stock_data?${params}`);
		const payload = await response.json();
		if (!response.ok) throw new Error(payload.error || 'Unable to load stock data');
		renderResult(payload);
	} catch (error) {
		result.innerHTML = `<p class="status error">${error.message}</p>`;
	}
});

function renderResult(payload) {
	const history = payload.data;
	const prediction = payload.prediction.forecast;
	const labels = history.map((point) => point.Date).concat(prediction.map((point) => point.date));
	const historicalPrices = history.map((point) => point.Close).concat(Array(prediction.length).fill(null));
	const predictedPrices = Array(history.length - 1).fill(null)
		.concat(history.at(-1).Close, prediction.map((point) => point.price));
	const info = payload.info;

	result.innerHTML = `
		<section class="summary">
			<div><span>Symbol</span><strong>${escapeHtml(info.name || 'Stock')}</strong></div>
			<div><span>Last close</span><strong>$${payload.prediction.last_close.toFixed(2)}</strong></div>
			<div><span>Model</span><strong>${payload.prediction.method}</strong></div>
		</section>
		<canvas id="priceChart" aria-label="Historical and predicted stock prices"></canvas>
		<p class="status">${escapeHtml(payload.news.message)}</p>`;

	chart?.destroy();
	chart = new Chart(document.getElementById('priceChart'), {
		type: 'line',
		data: { labels, datasets: [
			{ label: 'Historical close', data: historicalPrices, borderColor: '#166534', tension: 0.2 },
			{ label: 'Baseline forecast', data: predictedPrices, borderColor: '#c2410c', borderDash: [6, 4], tension: 0.2 }
		]},
		options: { responsive: true, interaction: { mode: 'index', intersect: false } }
	});
}

function escapeHtml(value) {
	return String(value).replace(/[&<>'"]/g, (character) => ({
		'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
	}[character]));
}

const today = new Date();
const monthAgo = new Date(today);
monthAgo.setMonth(today.getMonth() - 1);
document.getElementById('endDate').value = today.toISOString().slice(0, 10);
document.getElementById('startDate').value = monthAgo.toISOString().slice(0, 10);
