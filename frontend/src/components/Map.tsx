import { Text } from "@react-three/drei";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
// Importando o spritesheet da floresta
import forestSpritesheet from "../assets/spritesheets/forest/gentle forest (48x48 resize) v08.png";

// Interface para representar a posição de um sprite no spritesheet
interface SpritePosition {
  x: number; // posição X no spritesheet (0-15)
  y: number; // posição Y no spritesheet (0-15)
}

// Interface para representar uma posição na grid do mapa
interface GridPosition {
  x: number;
  y: number;
}

// Enum para os diferentes tipos de terreno
enum TerrainType {
  GRASS, // Grama (0)
  WATER, // Água (1)
  DIRT, // Terra (2)
  // Tipos removidos
}

// Interface para representar uma regra de tile
interface TileRule {
  terrain: TerrainType; // O tipo de terreno para esta regra
  center: SpritePosition; // O sprite central (default para este terreno)
  neighbors: {
    [key: string]: SpritePosition; // Sprite para cada padrão de vizinhos
  };
  randomVariations?: SpritePosition[]; // Variações aleatórias para este tipo de terreno
}

// Interface para configurações de geração de mapa aleatório
interface RandomMapConfig {
  seed?: number; // Seed para geração consistente
  waterPercentage?: number; // Porcentagem da área coberta por água (0-1)
  waterScale?: number; // Escala do ruído para água (número maior = lagos maiores)
  dirtPercentage?: number; // Porcentagem de terra
  smoothingIterations?: number; // Iterações de suavização para bordas mais naturais
}

interface MapProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  gridSize?: [number, number]; // [largura, altura] da grid
  tileSize?: number; // tamanho de cada tile em pixels
  tileMap?: (SpritePosition | null)[][]; // mapa de tiles personalizado
  terrainMap?: TerrainType[][]; // mapa de terrenos para usar com Rule Tiles
  randomIfNull?: boolean; // se true, usa sprites aleatórios para posições nulas
  useRuleTiles?: boolean; // se true, usa o sistema de Rule Tiles
  generateRandomMap?: boolean; // se true, gera um mapa aleatório ao carregar
  randomMapConfig?: RandomMapConfig; // configurações para geração de mapa aleatório
  showGrid?: boolean; // se true, mostra as linhas da grade
  showCoordinates?: boolean; // se true, mostra as coordenadas dos tiles
  debug?: boolean; // se true, ativa o modo de debug completo (grade + coordenadas)
  editable?: boolean; // se true, permite editar o mapa no modo debug
  onTileMapChange?: (newTileMap: (SpritePosition | null)[][]) => void; // callback quando o mapa é alterado
  onTerrainMapChange?: (newTerrainMap: TerrainType[][]) => void; // callback quando o mapa de terreno é alterado
}

const Map = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  gridSize = [20, 20], // Default grid size 20x20
  tileSize = 48, // Default tile size 48x48 pixels
  tileMap = undefined, // Mapa de tiles personalizado
  terrainMap = undefined, // Mapa de terrenos
  randomIfNull = true, // Por padrão, usa sprites aleatórios para posições nulas
  useRuleTiles = false, // Por padrão, não usa o sistema de Rule Tiles
  generateRandomMap = false, // Por padrão, não gera um mapa aleatório
  randomMapConfig = {
    waterPercentage: 0.25, // 25% de água
    waterScale: 0.08, // Lagos de tamanho médio
    dirtPercentage: 0.15, // 15% de terra
    smoothingIterations: 2, // 2 iterações de suavização
  }, // Configurações padrão para geração de mapa aleatório
  showGrid = false, // Por padrão, não mostra as linhas da grade
  showCoordinates = false, // Por padrão, não mostra as coordenadas dos tiles
  debug = false, // Por padrão, modo de debug desativado
  editable = false, // Por padrão, não permite editar o mapa
  onTileMapChange = undefined, // Callback quando o mapa é alterado
  onTerrainMapChange = undefined, // Callback quando o mapa de terreno é alterado
}: MapProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [textures, setTextures] = useState<THREE.Texture[][]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [selectedTile, setSelectedTile] = useState<GridPosition | null>(null);
  // Para o modo de edição, mantemos uma cópia local do tileMap que podemos modificar
  const [internalTileMap, setInternalTileMap] = useState<
    (SpritePosition | null)[][] | undefined
  >(tileMap);
  // Mapa de terreno interno
  const [internalTerrainMap, setInternalTerrainMap] = useState<
    TerrainType[][] | undefined
  >(terrainMap);
  // Sprite selecionado para pintar (no modo de edição)
  const [brushSprite, setBrushSprite] = useState<SpritePosition>({
    x: 0,
    y: 0,
  });
  // Terreno selecionado para pintar (no modo de edição de terreno)
  const [brushTerrain, setBrushTerrain] = useState<TerrainType>(
    TerrainType.GRASS
  );
  // Modo de edição atual (tile ou terreno)
  const [editMode, setEditMode] = useState<"tile" | "terrain">("tile");
  // Flag para indicar se já geramos um mapa aleatório
  const [randomMapGenerated, setRandomMapGenerated] = useState<boolean>(false);

  // Aplica configurações de debug
  const shouldShowGrid = showGrid || debug;
  const shouldShowCoordinates = showCoordinates || debug;
  const isEditable = editable && debug;

  // Dimensões do spritesheet
  const spriteSheetWidth = 768; // 16 colunas * 48px
  const spriteSheetHeight = 768; // 16 linhas * 48px
  const spritesPerRow = 16;
  const spritesPerColumn = 16;

  // Definição das regras de tile para cada tipo de terreno
  // Estas regras determinam qual sprite usar com base nos vizinhos
  const tileRules: TileRule[] = [
    // Grama (Grass)
    {
      terrain: TerrainType.GRASS,
      center: { x: 1, y: 5 }, // Grama central (corrigido)
      neighbors: {
        // Formato: "top,right,bottom,left,topRight,bottomRight,bottomLeft,topLeft"
        // onde 1 = mesmo terreno, 0 = terreno diferente, X = qualquer
        "1,1,1,1,1,1,1,1": { x: 1, y: 5 }, // Grama completa
        // Terra à direita, Grama à esquerda
        "X,0,X,1,X,X,X,X": { x: 0, y: 1 }, // Transição terra-grama
        // Terra em baixo, Grama em cima
        "0,X,1,X,X,X,X,X": { x: 1, y: 0 }, // Transição terra em baixo, grama em cima
      },
      randomVariations: [
        { x: 1, y: 5 }, // Grama tile 1
        { x: 2, y: 5 }, // Grama tile 2
        { x: 1, y: 6 }, // Grama tile 3
        { x: 2, y: 6 }, // Grama tile 4
      ],
    },
    // Água (Water)
    {
      terrain: TerrainType.WATER,
      center: { x: 1, y: 9 }, // Água central (corrigido)
      neighbors: {
        "1,1,1,1,1,1,1,1": { x: 1, y: 9 }, // Água completa
      },
      randomVariations: [
        { x: 1, y: 9 }, // Água tile 1
        { x: 2, y: 9 }, // Água tile 2
        { x: 1, y: 10 }, // Água tile 3
        { x: 2, y: 10 }, // Água tile 4
      ],
    },
    // Terra (Dirt)
    {
      terrain: TerrainType.DIRT,
      center: { x: 1, y: 1 }, // Terra central
      neighbors: {
        "1,1,1,1,1,1,1,1": { x: 1, y: 1 }, // Terra completa
        // Terra à esquerda, Grama à direita
        "X,1,X,0,X,X,X,X": { x: 3, y: 1 }, // Transição terra-grama
        // Terra em cima, Grama em baixo
        "1,X,0,X,X,X,X,X": { x: 1, y: 3 }, // Transição terra em cima, grama em baixo
      },
      randomVariations: [
        { x: 1, y: 1 }, // Terra tile 1
        { x: 1, y: 2 }, // Terra tile 2
        { x: 2, y: 1 }, // Terra tile 3
        { x: 2, y: 2 }, // Terra tile 4
      ],
    },
  ];

  // Atualiza o tileMap interno quando o tileMap de props muda
  useEffect(() => {
    setInternalTileMap(tileMap);
  }, [tileMap]);

  // Atualiza o terrainMap interno quando o terrainMap de props muda
  useEffect(() => {
    setInternalTerrainMap(terrainMap);
  }, [terrainMap]);

  // Função para gerar ruído de Perlin simples
  // Esta é uma implementação simples de ruído para manter o código conciso
  const perlinNoise = (x: number, y: number, seed: number = 0): number => {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;

    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);

    const topRight = (X + 1 + (Y + 1) * 57 + seed) & 255;
    const topLeft = (X + (Y + 1) * 57 + seed) & 255;
    const bottomRight = (X + 1 + Y * 57 + seed) & 255;
    const bottomLeft = (X + Y * 57 + seed) & 255;

    const u = fade(xf);
    const v = fade(yf);

    const a = lerp(
      grad(p[bottomLeft], xf, yf),
      grad(p[bottomRight], xf - 1, yf),
      u
    );
    const b = lerp(
      grad(p[topLeft], xf, yf - 1),
      grad(p[topRight], xf - 1, yf - 1),
      u
    );

    return 0.5 + 0.5 * lerp(a, b, v); // Normalize to 0-1
  };

  // Funções auxiliares para o ruído de Perlin
  const fade = (t: number): number => t * t * t * (t * (t * 6 - 15) + 10);
  const lerp = (a: number, b: number, t: number): number => a + t * (b - a);
  const grad = (hash: number, x: number, y: number): number => {
    const h = hash & 15;
    const grad_x = 1 + (h & 7); // Gradiente na direção x
    const grad_y = 1 + ((h >> 3) & 7); // Gradiente na direção y
    return (h & 8 ? -grad_x : grad_x) * x + (h & 4 ? -grad_y : grad_y) * y;
  };

  // Array de permutação para ruído de Perlin
  const p = Array(512)
    .fill(0)
    .map((_, i) => (i < 256 ? Math.floor(Math.random() * 256) : 0));
  for (let i = 256; i < 512; i++) {
    p[i] = p[i - 256];
  }

  // Função para gerar um mapa de terreno aleatório
  const generateRandomTerrainMap = () => {
    const width = gridSize[0];
    const height = gridSize[1];

    // Extrair e definir valores padrão para a configuração
    const {
      seed = Math.random() * 10000,
      waterPercentage = 0.25,
      waterScale = 0.08,
      dirtPercentage = 0.15,
      smoothingIterations = 2,
    } = randomMapConfig;

    // Inicializa o mapa de terreno
    const newTerrainMap: TerrainType[][] = [];

    // Usar seed para todos os ruídos
    const noiseSeed = seed;

    // Primeiro passo: gerar o mapa base com ruído de Perlin
    for (let y = 0; y < height; y++) {
      const row: TerrainType[] = [];
      for (let x = 0; x < width; x++) {
        // Gerar múltiplos valores de ruído para diferentes características
        const waterNoise = perlinNoise(
          x * waterScale,
          y * waterScale,
          noiseSeed
        );
        const dirtNoise = perlinNoise(
          x * 0.15 + 500,
          y * 0.15 + 500,
          noiseSeed + 1000
        );

        // Decidir o tipo de terreno com base nos valores do ruído
        if (waterNoise < waterPercentage) {
          // Água em áreas com valor baixo do ruído de água
          row.push(TerrainType.WATER);
        } else if (dirtNoise < dirtPercentage) {
          // Terra distribuída com base no ruído de terra
          row.push(TerrainType.DIRT);
        } else {
          // Padrão é grama
          row.push(TerrainType.GRASS);
        }
      }
      newTerrainMap.push(row);
    }

    // Segundo passo: suavizar o mapa para evitar blocos isolados
    const smoothedMap = [...newTerrainMap];

    for (let iteration = 0; iteration < smoothingIterations; iteration++) {
      const tempMap = JSON.parse(JSON.stringify(smoothedMap));

      for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
          // Contagem dos tipos de terreno vizinhos
          const neighborCounts: Record<number, number> = {};

          // Verificar os 8 vizinhos
          for (let ny = -1; ny <= 1; ny++) {
            for (let nx = -1; nx <= 1; nx++) {
              if (nx === 0 && ny === 0) continue; // Pula o próprio tile

              const neighborType = smoothedMap[y + ny][x + nx];
              neighborCounts[neighborType] =
                (neighborCounts[neighborType] || 0) + 1;
            }
          }

          // Encontrar o tipo de terreno mais comum nos vizinhos
          let mostCommonType = smoothedMap[y][x];
          let maxCount = 0;

          for (const [typeStr, count] of Object.entries(neighborCounts)) {
            const type = parseInt(typeStr);
            if (count > maxCount) {
              maxCount = count;
              mostCommonType = type;
            }
          }

          // Se houver 5 ou mais vizinhos de um tipo, muda para esse tipo (suavização)
          // Exceto água, que precisa de 6+ vizinhos para se espalhar
          const threshold = smoothedMap[y][x] === TerrainType.WATER ? 6 : 5;
          if (maxCount >= threshold) {
            tempMap[y][x] = mostCommonType;
          }
        }
      }

      // Atualiza o mapa suavizado para a próxima iteração
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          smoothedMap[y][x] = tempMap[y][x];
        }
      }
    }

    // Terceiro passo: adicionar elementos especiais
    // Adicionar areia ao redor da água
    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        // Se o tile for grama ou terra e estiver ao lado da água, há uma chance de ser areia
        if (
          smoothedMap[y][x] === TerrainType.GRASS ||
          smoothedMap[y][x] === TerrainType.DIRT
        ) {
          let hasWaterNeighbor = false;

          // Verificar os 4 vizinhos diretos
          const directions = [
            [-1, 0],
            [1, 0],
            [0, -1],
            [0, 1],
          ];
          for (const [dx, dy] of directions) {
            if (
              y + dy >= 0 &&
              y + dy < height &&
              x + dx >= 0 &&
              x + dx < width &&
              smoothedMap[y + dy][x + dx] === TerrainType.WATER
            ) {
              hasWaterNeighbor = true;
              break;
            }
          }

          if (hasWaterNeighbor) {
            smoothedMap[y][x] = TerrainType.DIRT;
          }
        }
      }
    }

    return smoothedMap;
  };

  // Inicializa o terrainMap interno se não foi fornecido e estamos usando Rule Tiles
  useEffect(() => {
    // Verificamos primeiro se devemos gerar um mapa aleatório
    if (useRuleTiles && generateRandomMap && !randomMapGenerated) {
      // Gerar mapa aleatório
      const randomMap = generateRandomTerrainMap();

      // Estatísticas do mapa gerado (para debug)
      const stats = {
        total: randomMap.flat().length,
        grass: randomMap.flat().filter((t) => t === TerrainType.GRASS).length,
        water: randomMap.flat().filter((t) => t === TerrainType.WATER).length,
        dirt: randomMap.flat().filter((t) => t === TerrainType.DIRT).length,
      };

      setInternalTerrainMap(randomMap);
      setRandomMapGenerated(true);

      // Notificar o componente pai da mudança
      if (onTerrainMapChange) {
        onTerrainMapChange(randomMap);
      }
    }
    // Se não estamos gerando um mapa aleatório, mas precisamos inicializar o terrainMap
    else if (
      useRuleTiles &&
      !internalTerrainMap &&
      gridSize &&
      !randomMapGenerated
    ) {
      const newTerrainMap: TerrainType[][] = [];
      for (let y = 0; y < gridSize[1]; y++) {
        const row: TerrainType[] = [];
        for (let x = 0; x < gridSize[0]; x++) {
          // Por padrão, inicia tudo como grama
          row.push(TerrainType.GRASS);
        }
        newTerrainMap.push(row);
      }
      setInternalTerrainMap(newTerrainMap);
    }
  }, [
    internalTerrainMap,
    gridSize,
    useRuleTiles,
    generateRandomMap,
    randomMapGenerated,
  ]);

  // Inicializa o tileMap interno se não foi fornecido
  useEffect(() => {
    if (!internalTileMap && gridSize && !useRuleTiles) {
      const newTileMap: (SpritePosition | null)[][] = [];
      for (let y = 0; y < gridSize[1]; y++) {
        const row: (SpritePosition | null)[] = [];
        for (let x = 0; x < gridSize[0]; x++) {
          row.push(null);
        }
        newTileMap.push(row);
      }
      setInternalTileMap(newTileMap);
    }
  }, [internalTileMap, gridSize, useRuleTiles]);

  // Função para alterar um tile no tileMap interno
  const updateTile = (x: number, y: number, sprite: SpritePosition | null) => {
    if (!internalTileMap) return;

    // Cria uma cópia profunda do tileMap para modificar
    const newTileMap = internalTileMap.map((row) => [...row]);

    // Atualiza o tile selecionado
    if (y >= 0 && y < newTileMap.length && x >= 0 && x < newTileMap[y].length) {
      newTileMap[y][x] = sprite;

      // Atualiza o estado interno
      setInternalTileMap(newTileMap);

      // Notifica o componente pai da mudança
      if (onTileMapChange) {
        onTileMapChange(newTileMap);
      }
    }
  };

  // Função para alterar um terreno no terrainMap interno
  const updateTerrain = (x: number, y: number, terrain: TerrainType) => {
    if (!internalTerrainMap) return;

    // Cria uma cópia profunda do terrainMap para modificar
    const newTerrainMap = internalTerrainMap.map((row) => [...row]);

    // Atualiza o terreno selecionado
    if (
      y >= 0 &&
      y < newTerrainMap.length &&
      x >= 0 &&
      x < newTerrainMap[y].length
    ) {
      newTerrainMap[y][x] = terrain;

      // Atualiza o estado interno
      setInternalTerrainMap(newTerrainMap);

      // Notifica o componente pai da mudança
      if (onTerrainMapChange) {
        onTerrainMapChange(newTerrainMap);
      }
    }
  };

  // Função para lidar com o clique em um tile
  const handleTileClick = (
    x: number,
    y: number,
    spriteX: number,
    spriteY: number
  ) => {
    if (!isEditable) return;

    if (editMode === "tile") {
      if (selectedTile && selectedTile.x === x && selectedTile.y === y) {
        // Se clicar no mesmo tile novamente, atualiza com o brush atual
        updateTile(x, y, { ...brushSprite });
        setSelectedTile(null);
      } else {
        // Seleciona o tile e define o brush com o sprite atual
        setSelectedTile({ x, y });
        setBrushSprite({ x: spriteX, y: spriteY });
      }
    } else if (editMode === "terrain" && internalTerrainMap) {
      // No modo de edição de terreno, simplesmente aplicamos o terreno selecionado
      updateTerrain(x, y, brushTerrain);
      // No modo de terreno, não selecionamos o tile
      setSelectedTile(null);
    }
  };

  // Função para trocar entre os modos de edição
  const toggleEditMode = () => {
    setEditMode(editMode === "tile" ? "terrain" : "tile");
    setSelectedTile(null);
  };

  // Função para obter o tipo de terreno em uma posição da grid
  const getTerrainAt = (x: number, y: number): TerrainType | null => {
    if (!internalTerrainMap) return null;
    if (y < 0 || y >= internalTerrainMap.length) return null;
    if (x < 0 || x >= internalTerrainMap[y].length) return null;
    return internalTerrainMap[y][x];
  };

  // Função para obter a regra de tile para um tipo de terreno
  const getTileRuleForTerrain = (terrain: TerrainType): TileRule | null => {
    return tileRules.find((rule) => rule.terrain === terrain) || null;
  };

  // Função para verificar se dois terrenos são do mesmo tipo
  const isSameTerrain = (
    a: TerrainType | null,
    b: TerrainType | null
  ): boolean => {
    if (a === null || b === null) return false;
    return a === b;
  };

  // Função para determinar o sprite correto baseado nas regras e vizinhos
  const determineSpriteForTile = (
    x: number,
    y: number,
    terrain: TerrainType
  ): SpritePosition => {
    const rule = getTileRuleForTerrain(terrain);
    if (!rule) return { x: 0, y: 0 }; // Fallback para um sprite padrão

    // Obtém os terrenos vizinhos
    const top = getTerrainAt(x, y - 1);
    const right = getTerrainAt(x + 1, y);
    const bottom = getTerrainAt(x, y + 1);
    const left = getTerrainAt(x - 1, y);
    const topRight = getTerrainAt(x + 1, y - 1);
    const bottomRight = getTerrainAt(x + 1, y + 1);
    const bottomLeft = getTerrainAt(x - 1, y + 1);
    const topLeft = getTerrainAt(x - 1, y - 1);

    // Cria a chave para buscar na tabela de regras
    const neighborKey = [
      isSameTerrain(top, terrain) ? "1" : "0",
      isSameTerrain(right, terrain) ? "1" : "0",
      isSameTerrain(bottom, terrain) ? "1" : "0",
      isSameTerrain(left, terrain) ? "1" : "0",
      isSameTerrain(topRight, terrain) ? "1" : "0",
      isSameTerrain(bottomRight, terrain) ? "1" : "0",
      isSameTerrain(bottomLeft, terrain) ? "1" : "0",
      isSameTerrain(topLeft, terrain) ? "1" : "0",
    ].join(",");

    // Função para gerar um valor pseudoaleatório determinístico baseado na posição
    const deterministicRandom = (posX: number, posY: number): number => {
      return (
        Math.abs(Math.sin(posX * 12.9898 + posY * 78.233) * 43758.5453) % 1
      );
    };

    // Busca a posição do sprite nas regras
    if (rule.neighbors[neighborKey]) {
      // Verificar para casos específicos de terra-grama
      if (terrain === TerrainType.GRASS && neighborKey === "X,0,X,1,X,X,X,X") {
        // Lógica determinística para escolher entre (0,1) e (0,2)
        return deterministicRandom(x, y) < 0.5
          ? { x: 0, y: 1 }
          : { x: 0, y: 2 };
      } else if (
        terrain === TerrainType.DIRT &&
        neighborKey === "X,1,X,0,X,X,X,X"
      ) {
        // Lógica determinística para escolher entre (3,1) e (4,1)
        return deterministicRandom(x, y) < 0.5
          ? { x: 3, y: 1 }
          : { x: 4, y: 1 };
      } else if (
        terrain === TerrainType.GRASS &&
        neighborKey === "0,X,1,X,X,X,X,X"
      ) {
        // Terra em baixo e grama em cima - escolher entre (1,0) e (2,0)
        return deterministicRandom(x, y) < 0.5
          ? { x: 1, y: 0 }
          : { x: 2, y: 0 };
      } else if (
        terrain === TerrainType.DIRT &&
        neighborKey === "1,X,0,X,X,X,X,X"
      ) {
        // Terra em cima e grama em baixo - escolher entre (1,3) e (2,3)
        return deterministicRandom(x, y) < 0.5
          ? { x: 1, y: 3 }
          : { x: 2, y: 3 };
      }
      // Outros casos, usar o valor definido
      return rule.neighbors[neighborKey];
    }

    // Verifica regras menos específicas (substituindo diagonais por X)
    const lessSpecificKey = [
      isSameTerrain(top, terrain) ? "1" : "0",
      isSameTerrain(right, terrain) ? "1" : "0",
      isSameTerrain(bottom, terrain) ? "1" : "0",
      isSameTerrain(left, terrain) ? "1" : "0",
      "X",
      "X",
      "X",
      "X",
    ].join(",");

    // Busca nas regras menos específicas
    for (const [key, sprite] of Object.entries(rule.neighbors)) {
      const pattern = key.split(",");
      if (pattern.length === 8) {
        let match = true;
        for (let i = 0; i < 8; i++) {
          if (
            pattern[i] !== "X" &&
            pattern[i] !== lessSpecificKey.split(",")[i]
          ) {
            match = false;
            break;
          }
        }
        if (match) {
          // Verificar os casos específicos aqui também
          if (terrain === TerrainType.GRASS && key === "X,0,X,1,X,X,X,X") {
            // Lógica determinística para escolher entre (0,1) e (0,2)
            return deterministicRandom(x, y) < 0.5
              ? { x: 0, y: 1 }
              : { x: 0, y: 2 };
          } else if (
            terrain === TerrainType.DIRT &&
            key === "X,1,X,0,X,X,X,X"
          ) {
            // Lógica determinística para escolher entre (3,1) e (4,1)
            return deterministicRandom(x, y) < 0.5
              ? { x: 3, y: 1 }
              : { x: 4, y: 1 };
          } else if (
            terrain === TerrainType.GRASS &&
            key === "0,X,1,X,X,X,X,X"
          ) {
            // Terra em baixo e grama em cima - escolher entre (1,0) e (2,0)
            return deterministicRandom(x, y) < 0.5
              ? { x: 1, y: 0 }
              : { x: 2, y: 0 };
          } else if (
            terrain === TerrainType.DIRT &&
            key === "1,X,0,X,X,X,X,X"
          ) {
            // Terra em cima e grama em baixo - escolher entre (1,3) e (2,3)
            return deterministicRandom(x, y) < 0.5
              ? { x: 1, y: 3 }
              : { x: 2, y: 3 };
          }
          return sprite;
        }
      }
    }

    // Se for para usar uma variação aleatória quando cercado por mesmo tipo de terreno
    if (
      neighborKey === "1,1,1,1,1,1,1,1" &&
      rule.randomVariations &&
      rule.randomVariations.length > 0 &&
      randomIfNull
    ) {
      // Deterministic random based on position (seeded by coordinates)
      const randomIndex = deterministicRandom(x, y);
      const index = Math.floor(randomIndex * rule.randomVariations.length);
      return rule.randomVariations[index];
    }

    // Retorna o sprite central como fallback
    return rule.center;
  };

  useEffect(() => {
    // Carrega o spritesheet
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load(
      forestSpritesheet,
      (loadedTexture) => {
        // Configurações do texture para renderização pixelada
        loadedTexture.magFilter = THREE.NearestFilter;
        loadedTexture.minFilter = THREE.NearestFilter;

        // Cria um array bidimensional para armazenar as texturas para cada tile
        const newTextures: THREE.Texture[][] = [];

        // Define o tamanho real da grid com base no tileMap, terrainMap ou no gridSize
        let effectiveGridWidth = gridSize[0];
        let effectiveGridHeight = gridSize[1];

        if (useRuleTiles && internalTerrainMap) {
          effectiveGridHeight = internalTerrainMap.length;
          effectiveGridWidth =
            internalTerrainMap[0]?.length || effectiveGridWidth;
        } else if (internalTileMap) {
          effectiveGridHeight = internalTileMap.length;
          effectiveGridWidth = internalTileMap[0]?.length || effectiveGridWidth;
        }

        // Define o sprite fixo que será usado em vez de sprites aleatórios
        const defaultSpriteX = 2; // Coluna 2 (os índices começam em 0)
        const defaultSpriteY = 6; // Linha 6 (os índices começam em 0)

        // Para cada célula na grid
        for (let y = 0; y < effectiveGridHeight; y++) {
          const row: THREE.Texture[] = [];
          for (let x = 0; x < effectiveGridWidth; x++) {
            let spriteX: number;
            let spriteY: number;

            // Decidir qual sprite usar com base no modo (Rule Tiles ou manual)
            if (
              useRuleTiles &&
              internalTerrainMap &&
              internalTerrainMap[y] &&
              internalTerrainMap[y][x] !== undefined
            ) {
              // Usando Rule Tiles: determina o sprite com base no terreno e seus vizinhos
              const terrain = internalTerrainMap[y][x];
              const spritePosition = determineSpriteForTile(x, y, terrain);
              spriteX = spritePosition.x;
              spriteY = spritePosition.y;
            } else if (
              internalTileMap &&
              internalTileMap[y] &&
              internalTileMap[y][x]
            ) {
              // Usando tileMap manual
              const tilePosition = internalTileMap[y][x];
              if (tilePosition !== null) {
                spriteX = tilePosition.x;
                spriteY = tilePosition.y;
              } else if (randomIfNull) {
                // Usando regras para terreno padrão (grama)
                if (Math.random() < 0.9) {
                  spriteX = defaultSpriteX;
                  spriteY = defaultSpriteY;
                } else {
                  // Pequena chance de variações
                  spriteX = 4 + Math.floor(Math.random() * 2);
                  spriteY = defaultSpriteY;
                }
              } else {
                // Se a posição é nula e randomIfNull é false, pula este tile
                row.push(null as unknown as THREE.Texture);
                continue;
              }
            } else {
              // Se não tiver um tileMap ou terrainMap, usamos o sprite fixo definido
              spriteX = defaultSpriteX;
              spriteY = defaultSpriteY;
            }

            // Cria uma nova texture com base no sprite escolhido
            const texture = loadedTexture.clone();

            // Define as coordenadas UV para o sprite específico
            texture.repeat.set(1 / spritesPerRow, 1 / spritesPerColumn);
            texture.offset.set(
              spriteX / spritesPerRow,
              1 - (spriteY + 1) / spritesPerColumn
            );

            // Armazenar os índices do sprite na textura para usar no modo de debug
            texture.userData = { spriteX, spriteY, gridX: x, gridY: y };

            row.push(texture);
          }
          newTextures.push(row);
        }

        setTextures(newTextures);
        setIsLoaded(true);
      },
      undefined,
      () => {
        // Silenciando erros de carregamento
        setIsLoaded(false);
      }
    );
  }, [
    gridSize,
    internalTileMap,
    internalTerrainMap,
    randomIfNull,
    useRuleTiles,
  ]);

  if (!isLoaded) {
    return null;
  }

  // Calcula o tamanho total da grid em unidades 3D
  const effectiveGridWidth = textures[0]?.length || 0;
  const effectiveGridHeight = textures.length || 0;
  const gridWidth = effectiveGridWidth * (tileSize / 100); // Convertendo de pixels para unidades 3D
  const gridHeight = effectiveGridHeight * (tileSize / 100);

  // Calcula o tamanho de um único tile em unidades 3D
  const tileWidth = tileSize / 100;
  const tileHeight = tileSize / 100;

  // Calcula a posição inicial (canto superior esquerdo da grid)
  const startX = position[0] - gridWidth / 2;
  const startY = position[1] + gridHeight / 2;

  // Cria as linhas de grade para o modo de debug
  const gridLines = shouldShowGrid ? (
    <>
      {/* Linhas horizontais */}
      {Array.from({ length: effectiveGridHeight + 1 }).map((_, index) => (
        <line key={`h-line-${index}`}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              array={
                new Float32Array([
                  startX,
                  startY - index * tileHeight,
                  0.01,
                  startX + gridWidth,
                  startY - index * tileHeight,
                  0.01,
                ])
              }
              count={2}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="red" />
        </line>
      ))}

      {/* Linhas verticais */}
      {Array.from({ length: effectiveGridWidth + 1 }).map((_, index) => (
        <line key={`v-line-${index}`}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              array={
                new Float32Array([
                  startX + index * tileWidth,
                  startY,
                  0.01,
                  startX + index * tileWidth,
                  startY - gridHeight,
                  0.01,
                ])
              }
              count={2}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="red" />
        </line>
      ))}
    </>
  ) : null;

  return (
    <group
      position={new THREE.Vector3(...position)}
      scale={new THREE.Vector3(...scale)}
    >
      {/* Tiles do mapa */}
      {textures.map((row, y) =>
        row.map((texture, x) => {
          // Pula tiles vazios
          if (!texture) return null;

          // Obtém os índices do sprite armazenados na textura
          const { spriteX, spriteY, gridX, gridY } = texture.userData || {
            spriteX: 0,
            spriteY: 0,
            gridX: x,
            gridY: y,
          };

          // Verifica se este tile está selecionado
          const isSelected =
            selectedTile &&
            selectedTile.x === gridX &&
            selectedTile.y === gridY;

          return (
            <mesh
              key={`tile-${x}-${y}`}
              position={[
                startX + x * tileWidth + tileWidth / 2,
                startY - y * tileHeight - tileHeight / 2,
                0,
              ]}
              onClick={() => handleTileClick(gridX, gridY, spriteX, spriteY)}
            >
              <planeGeometry args={[tileWidth, tileHeight]} />
              <meshBasicMaterial map={texture} transparent={true} />

              {/* Coordenadas para o modo de debug */}
              {shouldShowCoordinates && (
                <group position={[0, 0, 0.02]}>
                  {/* Fundo para o texto */}
                  <mesh position={[0, 0.05, 0]}>
                    <planeGeometry
                      args={[tileWidth * 0.8, tileHeight * 0.25]}
                    />
                    <meshBasicMaterial
                      color="rgba(0,0,0,0.5)"
                      transparent={true}
                    />
                  </mesh>

                  {/* Texto das coordenadas usando Text do drei */}
                  <Text
                    position={[0, 0.05, 0.001]}
                    fontSize={tileWidth * 0.2}
                    color="white"
                    anchorX="center"
                    anchorY="middle"
                  >
                    {useRuleTiles && internalTerrainMap
                      ? `T:${internalTerrainMap[y][x]} (${spriteX},${spriteY})`
                      : `${spriteX},${spriteY}`}
                  </Text>
                </group>
              )}

              {/* Destaque para o tile selecionado */}
              {isSelected && (
                <mesh position={[0, 0, 0.01]}>
                  <planeGeometry args={[tileWidth * 0.95, tileHeight * 0.95]} />
                  <meshBasicMaterial
                    color="yellow"
                    transparent={true}
                    opacity={0.3}
                  />
                </mesh>
              )}
            </mesh>
          );
        })
      )}

      {/* Linhas de grade para o modo de debug */}
      {gridLines}

      {/* Instruções do modo de edição */}
      {isEditable && (
        <>
          <Text
            position={[startX + gridWidth / 2, startY + tileHeight, 0]}
            fontSize={tileWidth * 0.3}
            color="white"
            anchorX="center"
            anchorY="middle"
          >
            {`Tile Editor Mode - ${
              editMode === "tile" ? "Sprite" : "Terrain"
            } - Click to select/update`}
          </Text>
          {isEditable && useRuleTiles && (
            <mesh
              position={[
                startX + gridWidth + tileWidth,
                startY - tileHeight,
                0,
              ]}
              onClick={() => toggleEditMode()}
            >
              <planeGeometry args={[tileWidth * 2, tileHeight]} />
              <meshBasicMaterial color="blue" />
              <Text
                position={[0, 0, 0.01]}
                fontSize={tileWidth * 0.2}
                color="white"
                anchorX="center"
                anchorY="middle"
              >
                {`Switch to ${editMode === "tile" ? "Terrain" : "Sprite"} Mode`}
              </Text>
            </mesh>
          )}
        </>
      )}
    </group>
  );
};

export default Map;
