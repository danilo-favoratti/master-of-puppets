# Game AI - Character Animation Demo

Este é um demo de animação de personagem 2D criado com React e React Three Fiber. Demonstra como implementar animações de sprite sheet com controle de tempo baseado na documentação do Mana Seed Character Base.

## Tecnologias Utilizadas

- **React**: Para a interface de usuário
- **TypeScript**: Para tipagem estática
- **React Three Fiber**: Para renderização 3D no navegador
- **Three.js**: Motor gráfico base

## Instruções para Execução

1. Instale as dependências:
   ```
   npm install
   ```

2. Execute o jogo em modo de desenvolvimento:
   ```
   npm run dev
   ```

3. Acesse `http://localhost:5173` no seu navegador

## Controles

- **Setas (↑, ↓, ←, →)**: Movimento do personagem
- **Shift + Setas**: Correr
- **Espaço**: Pular
- **Z**: Empurrar (Push)
- **X**: Puxar (Pull)

## Sistema de Animação

Este projeto implementa um sistema de animação baseado no sprite sheet "char_a_p1_0bas_humn_v00.png" do Mana Seed Character Base. As animações incluem:

- **Andar**: Frames 0-5 em cada linha direcional, temporização de 135ms por frame
- **Correr**: Sequência de frames 1,2,7,4,5,8 com temporização variável (80/55/125/80/55/125ms)
- **Empurrar**: Frames 1-2 em cada linha direcional, temporização de 300ms por frame
- **Puxar**: Frames 3-4 em cada linha direcional, temporização de 400ms por frame
- **Pular**: Frames 5-7 em cada linha direcional, com o primeiro frame repetido no final, temporização de 300/150/100/300ms

## Estrutura do Projeto

- `src/components/`: Componentes React para o jogo
  - `CharacterSprite.tsx`: Componente que implementa o sistema de animação
  - `Game.tsx`: Componente principal do jogo que controla o personagem
  - `GameUI.tsx`: Interface do usuário
- `src/hooks/`: Custom hooks
  - `useKeyboardControls.ts`: Hook para controle do teclado
- `src/assets/`: Assets do jogo
  - `char_a_p1_0bas_humn_v00.png`: Sprite sheet principal do personagem

## Referências

As animações seguem as recomendações da documentação do Mana Seed Character Base, incluindo:
- Convenções de nomenclatura para os sprites
- Configuração da animação de corrida
- Guia de temporização das animações
- Implementação das animações de empurrar, puxar, pular e escalar

## Licença

MIT 