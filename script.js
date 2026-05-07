const dropZone = document.getElementById('drop-zone');
const dropContent = document.getElementById('drop-zone-content');
const fileInput = document.getElementById('file-input');

// Ao clicar na zona, abre o seletor de arquivos
dropZone.onclick = () => fileInput.click();

// Escuta quando um arquivo é selecionado via seletor
fileInput.onchange = (e) => {
    if (e.target.files.length > 0) {
        exibirNomeArquivo(e.target.files[0]);
    }
};

// Funções para Arrastar e Soltar (Drag and Drop)
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('file-hover'); // Adiciona destaque visual
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('file-hover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('file-hover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files; // Sincroniza os arquivos soltos com o input
        exibirNomeArquivo(files[0]);
    }
});

// Função que atualiza a interface com o nome do arquivo
function exibirNomeArquivo(arquivo) {
    const nome = arquivo.name;
    const extensao = nome.split('.').pop().toLowerCase();
    let icone = (extensao === 'csv') ? 'fa-file-csv' : 'fa-file-excel';

    // 1. Atualiza o conteúdo da zona de drop
    dropContent.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
            <i class="fas ${icone}" style="color: #15803d; font-size: 3.5rem;"></i>
            <p style="margin: 10px 0 5px 0; font-size: 1.1rem; color: #1e293b;">
                <strong>Arquivo carregado:</strong><br>
                <span style="word-break: break-all;">${nome}</span>
            </p>
            <span style="color: #16a34a; font-size: 0.9rem; display: flex; align-items: center; gap: 5px; justify-content: center;">
                <i class="fas fa-check-circle"></i> Pronto para análise
            </span>
        </div>
    `;
    
    // 2. ESCONDER o botão de seleção inicial
    const btnInicial = document.getElementById('btn-selecionar-inicial');
    if (btnInicial) {
        btnInicial.style.display = 'none';
    }

    // 3. MOSTRAR o novo botão de envio na action-area
    const actionArea = document.getElementById('action-area');
    actionArea.innerHTML = `
        <button id="btn-enviar" class="btn-upload" style="width: 100%; background-color: #15803d; animation: fadeIn 0.5s ease;">
            ENVIAR <i class="fas fa-arrow-right" style="margin-left: 10px;"></i>
        </button>
    `;

    // Evento de clique para mudar de página
    document.getElementById('btn-enviar').onclick = function() {
        window.location.href = 'analise.html'; 
    };

    dropZone.style.borderColor = "#15803d";

    // Evento de clique real para processar os dados
document.getElementById('btn-enviar').onclick = async function() {
    const btn = document.getElementById('btn-enviar');
    btn.innerHTML = 'PROCESSANDO... <i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        // Envia para o servidor Python
        const response = await fetch('http://127.0.0.1:5000/analisar', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const erroData = await response.json();
            throw new Error(erroData.error || 'Erro no servidor');
        }

        const data = await response.json();
        
        // GUARDA OS DADOS NA MOCHILA
        localStorage.setItem('dadosAnalise', JSON.stringify(data));

        // AGORA SIM, MUDA DE PÁGINA
        window.location.href = 'analise.html'; 

    } catch (error) {
        console.error("Erro:", error);
        alert("Erro ao analisar dados de Ourinhos: " + error.message);
        btn.innerHTML = 'TENTAR NOVAMENTE <i class="fas fa-arrow-right"></i>';
        btn.disabled = false;
    }
};
}