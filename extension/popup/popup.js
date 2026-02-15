// popup.js - Mejorado para PeliculasGD y UI
document.addEventListener('DOMContentLoaded', async () => {
    const resolveBtn = document.getElementById('resolve-btn');
    const logDiv = document.getElementById('log');
    const resultBox = document.getElementById('result-box');
    const finalLinkSpan = document.getElementById('final-link');
    const copyBtn = document.getElementById('copy-btn');
    const formatControls = document.getElementById('format-controls');
    const movieInfo = document.getElementById('movie-info');
    const movieTitleElem = document.getElementById('movie-title');

    function log(msg) {
        const time = new Date().toLocaleTimeString();
        logDiv.innerHTML += `<div>[${time}] ${msg}</div>`;
        logDiv.scrollTop = logDiv.scrollHeight;
    }

    // 1. Detectar Sitio
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return log("Error: No se detectó pestaña.");

    const url = tab.url;
    let isPeliculasGD = url.includes('peliculasgd.net') || url.includes('peliculasgd.co');

    if (isPeliculasGD) {
        // Modo PeliculasGD: Ocultar selectores, mostrar título
        formatControls.style.display = 'none';
        movieInfo.style.display = 'block';
        
        // Limpiar título de la pestaña (ej: "Ver Matrix 4... - PeliculasGD")
        let cleanTitle = tab.title.replace(/^Ver\s+/i, '').split('-')[0].trim();
        if (!cleanTitle) cleanTitle = "Película Desconocida";
        movieTitleElem.textContent = cleanTitle;
        
        resolveBtn.textContent = "OBTENER ENLACE";
    } else {
        // Modo Normal (HackStore u otros)
        movieInfo.style.display = 'none';
        formatControls.style.display = 'grid'; // Restaurar grid del CSS
        resolveBtn.textContent = "ANALIZAR PÁGINA";
    }

    // 2. Acción del Botón
    resolveBtn.addEventListener('click', () => {
        resolveBtn.disabled = true;
        resolveBtn.style.opacity = "0.7";
        resolveBtn.textContent = "PROCESANDO...";
        
        const quality = document.getElementById('quality').value;
        const format = document.getElementById('format').value;

        log(`Iniciando resolución en: ${new URL(url).hostname}...`);
        
        chrome.runtime.sendMessage({
            action: "START_RESOLUTION",
            url: url,
            criteria: { quality, format }
        }, (response) => {
            if (chrome.runtime.lastError) {
                log("Error: El servicio no responde. Recarga la extensión.");
                resolveBtn.disabled = false;
            } else {
                log("Solicitud enviada al núcleo.");
            }
        });
    });

    // 3. Escuchar Respuestas
    chrome.runtime.onMessage.addListener((msg) => {
        if (msg.action === "LOG") log(msg.message);
        if (msg.action === "RESOLVED") {
            resultBox.style.display = "block";
            finalLinkSpan.innerText = msg.url;
            log("✅ ¡Enlace capturado con éxito!");
            resolveBtn.textContent = "¡LISTO!";
            resolveBtn.disabled = false;
            resolveBtn.style.opacity = "1";
        }
    });
    
    // Copiar al portapapeles
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(finalLinkSpan.innerText);
        copyBtn.innerText = "¡COPIADO!";
        setTimeout(() => copyBtn.innerText = "COPIAR ENLACE", 2000);
    });
});
