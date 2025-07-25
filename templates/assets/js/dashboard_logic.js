
        let cpuChart, ramChart, diskChart;

        function setupCharts() {
            cpuChart = new Chart(document.getElementById('cpuChart'), {
                type: 'line',
                data: {
                    labels: [], datasets: [{ label: 'CPU %', data: [], borderColor: '#00ffcc' }]
                },
                options: { responsive: true, animation: false }
            });

            ramChart = new Chart(document.getElementById('ramChart'), {
                type: 'bar',
                data: {
                    labels: ['Used', 'Free'],
                    datasets: [{ label: 'RAM (MB)', data: [0, 0], backgroundColor: ['#ff4081', '#00ffcc'] }]
                },
                options: { responsive: true, animation: false }
            });

            diskChart = new Chart(document.getElementById('diskChart'), {
                type: 'bar',
                data: {
                    labels: ['Used', 'Free'],
                    datasets: [{ label: 'Disk (GB)', data: [0, 0], backgroundColor: ['#ffa500', '#00ffcc'] }]
                },
                options: { responsive: true, animation: false }
            });
        }

        async function fetchStats() {
            const res = await fetch('/sysmon/data');
            const data = await res.json();

            const time = new Date().toLocaleTimeString();
            if (cpuChart.data.labels.length > 20) {
                cpuChart.data.labels.shift();
                cpuChart.data.datasets[0].data.shift();
            }
            cpuChart.data.labels.push(time);
            cpuChart.data.datasets[0].data.push(data.cpu);
            cpuChart.update();

            ramChart.data.datasets[0].data = [data.ram_used, data.ram_total - data.ram_used];
            ramChart.update();

            diskChart.data.datasets[0].data = [data.disk_used, data.disk_total - data.disk_used];
            diskChart.update();

            document.getElementById('netStats').textContent =
                `Sent: ${data.net_sent} MB | Received: ${data.net_recv} MB`;

            document.getElementById('batteryStats').textContent =
                data.battery !== null ?
                `Battery: ${data.battery.percent}% ${data.battery.plugged ? '(Charging)' : ''}` :
                'Battery info not available';

            document.getElementById('currentUsers').textContent = data.current_visitors;
            document.getElementById('totalUsers').textContent = data.total_visitors;
            document.getElementById('maintenanceStatus').textContent = data.maintenance ? '🛠 Maintenance Mode ON' : '';
        }

        setupCharts();
        setInterval(fetchStats, 1000);
        fetchStats();
