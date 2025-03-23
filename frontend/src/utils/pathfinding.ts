interface Node {
  x: number;
  y: number;
  g: number;
  h: number;
  f: number;
  parent: Node | null;
}

export function findPath(start: Point, end: Point, grid: boolean[][]): Point[] {
  const openList: Node[] = [];
  const closedList: Node[] = [];
  
  const startNode: Node = {
    x: start.x,
    y: start.y,
    g: 0,
    h: 0,
    f: 0,
    parent: null
  };
  
  openList.push(startNode);
  
  while (openList.length > 0) {
    // Encontrar nó com menor f
    let currentNode = openList[0];
    let currentIndex = 0;
    
    openList.forEach((node, index) => {
      if (node.f < currentNode.f) {
        currentNode = node;
        currentIndex = index;
      }
    });
    
    // Mover para closed list
    openList.splice(currentIndex, 1);
    closedList.push(currentNode);
    
    // Encontrou o destino
    if (currentNode.x === end.x && currentNode.y === end.y) {
      const path: Point[] = [];
      let current: Node | null = currentNode;
      
      while (current) {
        path.push({ x: current.x, y: current.y });
        current = current.parent;
      }
      
      return path.reverse();
    }
    
    // Gerar vizinhos
    const neighbors: Node[] = [];
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        if (dx === 0 && dy === 0) continue;
        
        const newX = currentNode.x + dx;
        const newY = currentNode.y + dy;
        
        // Verificar se está dentro do grid e é walkable
        if (newX >= 0 && newX < grid[0].length && 
            newY >= 0 && newY < grid.length && 
            grid[newY][newX]) {
          
          neighbors.push({
            x: newX,
            y: newY,
            g: 0,
            h: 0,
            f: 0,
            parent: currentNode
          });
        }
      }
    }
    
    // Para cada vizinho...
    neighbors.forEach(neighbor => {
      if (closedList.find(node => node.x === neighbor.x && node.y === neighbor.y)) {
        return;
      }
      
      neighbor.g = currentNode.g + 1;
      neighbor.h = Math.abs(end.x - neighbor.x) + Math.abs(end.y - neighbor.y);
      neighbor.f = neighbor.g + neighbor.h;
      
      const openNode = openList.find(node => node.x === neighbor.x && node.y === neighbor.y);
      if (openNode && openNode.g < neighbor.g) {
        return;
      }
      
      openList.push(neighbor);
    });
  }
  
  return []; // Não encontrou caminho
} 