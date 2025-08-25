// {{PROJECT_NAME}} - JavaScript principal

console.log('{{PROJECT_NAME}} cargado correctamente');

function saludar() {
    alert('¡Hola desde {{PROJECT_NAME}}!');
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado - Proyecto listo');
    
    // Agregar animación suave al botón
    const button = document.querySelector('button');
    if (button) {
        button.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
        });
    }
});

// Funciones útiles para el proyecto
const utils = {
    // Función para hacer requests
    async fetchData(url) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    },
    
    // Función para formatear fechas
    formatDate(date) {
        return new Date(date).toLocaleDateString('es-ES');
    }
};

window.utils = utils;
