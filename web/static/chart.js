// 📊 CUSTOM CHART.JS STYLING FOR GAMING UI

document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById('statsChart');

    if (!ctx) return;

    // Check if chartData is defined (passed from Python/HTML)
    if (typeof chartData === 'undefined') {
        console.warn('❌ chartData object missing!');
        return;
    }

    // 🎨 Neon Color Palette
    const colors = {
        cyan: '#00d9ff',     // Wins
        pink: '#ff006e',     // Losses
        purple: '#8e44ad',   // Highlights
        dark: '#1a1a2e',     // Background
        text: '#e0e0e0'      // Text
    };

    // Calculate Win Rate for Center Text
    const totalGames = chartData.games_won + chartData.games_lost;
    const winRate = totalGames > 0
        ? Math.round((chartData.games_won / totalGames) * 100)
        : 0;

    // 🎯 Center Text Plugin
    const centerText = {
        id: 'centerText',
        beforeDraw: function (chart) {
            if (chart.config.type !== 'doughnut') return;
            var width = chart.width,
                height = chart.height,
                ctx = chart.ctx;

            ctx.restore();
            var fontSize = (height / 114).toFixed(2);
            ctx.font = "bold " + fontSize + "em 'Orbitron', 'Roboto', sans-serif";
            ctx.textBaseline = "middle";
            ctx.fillStyle = colors.text;

            var text = winRate + "%",
                textX = Math.round((width - ctx.measureText(text).width) / 2),
                textY = height / 2;

            ctx.fillText(text, textX, textY);

            // Subtext "Win Rate"
            ctx.font = "normal " + (fontSize * 0.4) + "em sans-serif";
            ctx.fillStyle = "#888";
            var subtext = "Win Rate",
                subtextX = Math.round((width - ctx.measureText(subtext).width) / 2),
                subtextY = height / 2 + 25;

            ctx.fillText(subtext, subtextX, subtextY);
            ctx.save();
        }
    };

    // 🚀 Create The Chart
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Wins', 'Losses'],
            datasets: [{
                data: [chartData.games_won, chartData.games_lost],
                backgroundColor: [
                    colors.cyan,  // Wins
                    colors.pink   // Losses
                ],
                borderColor: colors.dark,
                borderWidth: 4,
                hoverOffset: 15,
                hoverBorderColor: colors.purple,
                hoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Allows custom height
            cutout: '75%', // Thinner ring for modern look
            animation: {
                animateScale: true,
                animateRotate: true,
                duration: 2000,
                easing: 'easeOutQuart'
            },
            layout: {
                padding: 20
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: colors.text,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 20,
                        font: {
                            size: 14,
                            family: "'Roboto', sans-serif"
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleColor: colors.cyan,
                    bodyColor: colors.text,
                    borderColor: colors.purple,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function (context) {
                            let label = context.label || '';
                            let value = context.raw || 0;
                            let percentage = totalGames > 0 ? Math.round((value / totalGames) * 100) + '%' : '0%';
                            return ` ${label}: ${value} (${percentage})`;
                        }
                    }
                },
                title: {
                    display: false
                }
            }
        },
        plugins: [centerText] // Register custom plugin
    });
});
