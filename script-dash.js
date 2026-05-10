
const dados = JSON.parse(localStorage.getItem('dadosAnalise'));

if (dados) {
    const elementoTotal = document.getElementById('total-gasto');
    const valorTotal = dados.total_valor;

    // Formatação em Moeda Brasileira
    elementoTotal.innerText = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valorTotal);

    // Ajuste dinâmico de fonte: 1 milhão ou mais
    if (valorTotal >= 100000000) {
        elementoTotal.classList.add('fonte-pequena');
    } else {
        elementoTotal.classList.remove('fonte-pequena');
    }

    // Preenchimento dos outros cards
    document.getElementById('total-registros').innerText = dados.qtd_registros.toLocaleString('pt-BR');
    document.getElementById('periodo-analise').innerText = dados.periodo || "Não identificado";

    // --- GRÁFICO 1: BENFORD ---
    const ctx = document.getElementById('graficoBenford').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dados.labels,
            datasets: [{
                label: 'Frequência Real (Ourinhos)',
                data: dados.real,
                backgroundColor: 'rgba(27, 67, 50, 0.8)',
                borderRadius: 10,
                barPercentage: 0.6
            }, {
                label: 'Lei de Benford (Teórica)',
                data: dados.teorica,
                type: 'line',
                borderColor: '#e3230e',
                borderWidth: 4,
                pointBackgroundColor: '#e3230e',
                borderWidth: 4,
                pointRadius: 5,
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle',
                        boxWidth: 8,
                        boxHeight: 8,
                        padding: 20,
                        font: {
                            family: 'Segoe UI',
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'DISTRIBUIÇÃO DO PRIMEIRO DÍGITO',
                    align: 'center',
                    color: '#1e293b',
                    font: { size: 16, weight: 'bold' },
                    padding: { bottom: 30 }
                }
            },
            scales: {
                y: { ticks: { callback: value => value + '%' } }
            }
        }
    });

    // --- GRÁFICO 3: FUNÇÕES ---
    if (dados.gastos_por_funcao) {
        const ctxFuncao = document.getElementById('graficoFuncoes').getContext('2d');
        new Chart(ctxFuncao, {
            type: 'bar',
            data: {
                labels: dados.gastos_por_funcao.labels,
                datasets: [{
                    label: 'Total Gasto (R$)',
                    data: dados.gastos_por_funcao.valores,
                    backgroundColor: 'rgba(5, 150, 105, 0.7)',
                    borderColor: '#059669',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'GASTOS POR FUNÇÃO',
                        align: 'center', // PADRONIZADO CENTRALIZADO
                        color: '#1e293b',
                        font: { size: 16, weight: 'bold' },
                        padding: { bottom: 30 }
                    }
                }
            }
        });
    }

    // --- TABELA CONJUNTA ---
    const tableBody = document.getElementById('body-conjunto');
    const tableHeader = document.getElementById('header-d2');

    if (dados.tabela_conjunta) {
        tableHeader.innerHTML = '<th>1° \\ 2°</th>';
        for (let i = 0; i <= 9; i++) {
            let th = document.createElement('th');
            th.innerText = i;
            tableHeader.appendChild(th);
        }

        tableBody.innerHTML = '';
        dados.tabela_conjunta.forEach((linha, idx) => {
            let tr = document.createElement('tr');
            let tdTitle = document.createElement('td');
            tdTitle.innerHTML = `<b>${idx + 1}</b>`;
            tr.appendChild(tdTitle);

            linha.forEach(celula => {
                let td = document.createElement('td');
                const valTeorico = celula.teorico || celula.teorica;
                const valReal = celula.real;

                td.innerHTML = `
                            <div class="celula-info">
                                <span class="val-real">${valReal.toFixed(4).replace('.', ',')}</span>
                                <span class="val-teorico">T: ${valTeorico.toFixed(4).replace('.', ',')}</span>
                            </div>
                        `;

                if (Math.abs(valTeorico - valReal) > 0.01) {
                    td.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                }
                tr.appendChild(td);
            });
            tableBody.appendChild(tr);
        });
    }

    // --- GRÁFICO 4: SAZONALIDADE ---
    if (dados.gastos_por_mes) {
        const ctxSazonal = document.getElementById('graficoSazonalidade').getContext('2d');
        new Chart(ctxSazonal, {
            type: 'line',
            data: {
                labels: dados.gastos_por_mes.labels,
                datasets: [{
                    label: 'Total Mensal (R$)',
                    data: dados.gastos_por_mes.valores,
                    borderColor: '#10b981', // Verde
                    backgroundColor: 'rgba(16, 185, 129, 0.1)', // Preenchimento leve
                    fill: true,
                    tension: 0.4, // Curva suave
                    pointRadius: 4,
                    pointBackgroundColor: '#10b981'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            boxWidth: 8, // Bolinha pequena e padronizada
                            boxHeight: 8,
                            font: { weight: 'bold' }
                        }
                    },
                    title: {
                        display: true,
                        text: 'EVOLUÇÃO MENSAL DOS GASTOS (SAZONALIDADE)',
                        align: 'center',
                        color: '#1e293b',
                        font: { size: 16, weight: 'bold' },
                        padding: { bottom: 30 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: value => 'R$ ' + value.toLocaleString('pt-BR') }
                    }
                }
            }
        });
    }
    document.getElementById('periodo-analise').innerText = dados.periodo || "N/A";

    //TESTES Z e QUI
    if (dados.valores_z) {
        const headerZ = document.getElementById('header-z');
        const rowZ = document.getElementById('row-z-values');

        // Limpar para evitar duplicatas
        headerZ.innerHTML = '<th>Dígito</th>';
        rowZ.innerHTML = '<td><b>Valor Z</b></td>';

        dados.valores_z.forEach((z, index) => {
            const digito = index + 1;

            // Adiciona cabeçalho
            const th = document.createElement('th');
            th.innerText = digito;
            headerZ.appendChild(th);

            // Adiciona valor Z com destaque se for > 1.96
            const td = document.createElement('td');
            td.innerText = z.toFixed(2).replace('.', ',');

            if (z > 1.96) {
                td.style.backgroundColor = 'rgba(239, 68, 68, 0.2)';
                td.style.color = '#b91c1c';
                td.style.fontWeight = 'bold';
                td.title = "Desvio significativo detectado!";
            }

            rowZ.appendChild(td);
        });
    }

    const valorQui = dados.qui_quadrado_matriz;
    const elementoValor = document.getElementById('valor-qui');
    const elementoStatus = document.getElementById('status-qui');
    const elementoContainer = document.getElementById('alerta-qui');

    elementoValor.innerText = valorQui.toLocaleString('pt-BR');

    // Valor crítico para 81 graus de liberdade é ~101.8
    if (valorQui > 101.8) {
        elementoContainer.style.backgroundColor = '#fee2e2'; // Vermelho claro
        elementoContainer.style.color = '#991b1b';
        elementoStatus.innerText = "⚠️ Desvio Global Significativo: A matriz não segue o padrão de Benford.";
    } else {
        elementoContainer.style.backgroundColor = '#dcfce7'; // Verde claro
        elementoContainer.style.color = '#166534';
        elementoStatus.innerText = "✅ Conformidade Detectada: Os dados seguem o padrão global.";
    }



} else {
    window.location.href = 'index.html';
}