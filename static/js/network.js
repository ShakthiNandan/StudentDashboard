// Network diagram visualization
document.addEventListener('DOMContentLoaded', function() {
    // Function to create network diagram
    function createNetworkDiagram(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Create network visualization
        const network = new vis.Network(container, data, {
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    size: 12
                },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                width: 2,
                shadow: true,
                smooth: {
                    type: 'continuous'
                }
            },
            physics: {
                stabilization: false,
                barnesHut: {
                    gravitationalConstant: -80000,
                    springConstant: 0.001,
                    springLength: 200
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200
            }
        });
        
        // Add animation
        network.on('stabilizationProgress', function(params) {
            container.style.opacity = params.iterations / params.total;
        });
        
        network.on('stabilizationIterationsDone', function() {
            container.style.opacity = 1;
        });
        
        return network;
    }
    
    // Initialize network diagrams if data is available
    const networkContainers = document.querySelectorAll('.network-container');
    networkContainers.forEach(container => {
        const data = JSON.parse(container.dataset.network || '{"nodes":[],"edges":[]}');
        createNetworkDiagram(container.id, data);
    });
}); 