/* Draws Chart.js charts from data that Django puts into the page.
   Usage in a template:
     {{ chart_data|json_script:"my-data" }}
     <canvas data-chart-source="my-data" data-chart-type="doughnut"></canvas>
   chart_data looks like: {"labels": [...], "values": [...], "label": "Applications"} */
(function () {
  var PALETTE = ['#4f46e5', '#06b6d4', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#64748b', '#ec4899'];

  function draw(canvas) {
    var source = document.getElementById(canvas.getAttribute('data-chart-source'));
    if (!source || typeof Chart === 'undefined') { return; }
    var data = JSON.parse(source.textContent);
    var type = canvas.getAttribute('data-chart-type') || 'bar';
    var total = data.values.reduce(function (a, b) { return a + b; }, 0);

    if (total === 0) {  // nothing to draw: show a friendly message instead of an empty chart
      canvas.insertAdjacentHTML('afterend', '<p class="text-muted text-center small mb-0">No data yet.</p>');
      canvas.style.display = 'none';
      return;
    }

    var isRound = (type === 'doughnut' || type === 'pie');
    new Chart(canvas, {
      type: type,
      data: {
        labels: data.labels,
        datasets: [{
          label: data.label || '',
          data: data.values,
          backgroundColor: isRound ? PALETTE : (type === 'line' ? 'rgba(79,70,229,.15)' : PALETTE[0]),
          borderColor: type === 'line' ? PALETTE[0] : undefined,
          fill: type === 'line',
          tension: 0.3,
          borderRadius: type === 'bar' ? 6 : 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: isRound, position: 'bottom' } },
        scales: isRound ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('canvas[data-chart-source]').forEach(draw);
  });
})();
