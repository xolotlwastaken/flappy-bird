const canvas = document.getElementById("gameCanvas");
const context = canvas.getContext("2d");

// Canvas dimensions
canvas.width = 320;
canvas.height = 480;

// Game assets
const bird = new Image();
const bg = new Image();
const fg = new Image();
const pipeNorth = new Image();
const pipeSouth = new Image();

bird.src = "/static/assets/bird.png";
bg.src = "/static/assets/background.png";
fg.src = "/static/assets/fg.png";
pipeNorth.src = "/static/assets/pipeNorth.png";
pipeSouth.src = "/static/assets/pipeSouth.png";

// Variables
let gap = 200;
let constant;
let bX = 50; // Bird X position
let bY = 150; // Bird Y position
let gravity = 0.1; // Reduced gravity for slower falling
let velocity = 0; // Bird's velocity
let lift = -3.5; // Reduced upward force to make the bird movement smoother
let score = 0;

// Audio
const fly = new Audio();
const scor = new Audio();

fly.src = "/static/assets/fly.mp3";
scor.src = "/static/assets/score.mp3";

// Pipe coordinates
let pipes = [];
pipes[0] = {
  x: canvas.width,
  y: Math.floor(Math.random() * (canvas.height - gap - fg.height)) - pipeNorth.height,
};

// Key press event
document.addEventListener("keydown", moveUp);
document.addEventListener("touchstart", moveUp);

function moveUp() {
  velocity = lift; // Apply upward force
  fly.play();
}


// To save the user's highest score
function saveHighestScore(score) {
  fetch('/save_score', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ score: score }),
  })
  .then(response => response.json())
  .then(data => {
    console.log('Success:', data);
  })
  .catch((error) => {
    console.error('Error:', error);
  });
}

// Function to fetch and display the leaderboard
function showLeaderboard() {
    fetch('/api/leaderboard')
        .then(response => response.json())
        .then(data => {
            const leaderboardTable = document.getElementById('leaderboardTable').getElementsByTagName('tbody')[0];
            leaderboardTable.innerHTML = ''; // Clear existing rows
            data.leaderboard.forEach(user => {
                const row = leaderboardTable.insertRow();
                const usernameCell = row.insertCell(0);
                const scoreCell = row.insertCell(1);
                usernameCell.textContent = user.username;
                scoreCell.textContent = user.highest_score;
            });
            document.getElementById('leaderboardModal').style.display = 'block';
        })
        .catch(error => console.error('Error fetching leaderboard:', error));
}

// Function to close the leaderboard modal
function closeLeaderboard() {
    document.getElementById('leaderboardModal').style.display = 'none';
}

// Game loop and other game logic...

// Example function to handle game over
function gameOver() {
    alert("Game Over! Score: " + score);
    saveHighestScore(score);
    showLeaderboard();
    location.reload();
}

// Game loop
function draw() {
  context.drawImage(bg, 0, 0);

  for (let i = 0; i < pipes.length; i++) {
    constant = pipeNorth.height + gap;

    // Draw pipes
    context.drawImage(pipeNorth, pipes[i].x, pipes[i].y);
    context.drawImage(pipeSouth, pipes[i].x, pipes[i].y + constant);

    // Debug outlines for the pipes
    context.strokeStyle = "green";
    context.strokeRect(
      pipes[i].x,
      pipes[i].y,
      pipeNorth.width,
      pipeNorth.height 
    );
    context.strokeRect(
      pipes[i].x,
      pipes[i].y + constant,
      pipeSouth.width,
      canvas.height - (pipes[i].y + constant)
    );

    pipes[i].x--; // Move pipes left

    // Generate new pipes
    if (pipes[i].x === 125) {
      pipes.push({
        x: canvas.width,
        y: Math.floor(Math.random() * (canvas.height - gap - fg.height)) - pipeNorth.height,
      });
    }

    // Detect collision (with edge case improvement)
    if (
      (bX + bird.width > pipes[i].x &&
        bX < pipes[i].x + pipeNorth.width &&
        (bY < pipes[i].y + pipeNorth.height || bY + bird.height > pipes[i].y + constant)) ||
      bY + bird.height >= canvas.height - fg.height ||
      bY <= 0
    ) {
      gameOver();
      return;
    }

    // Update score
    if (pipes[i].x === 5) {
      score++;
      scor.play();

      // Dynamically reduce the gap every 10 points
      if (score % 5 === 0 && gap > 120) {
        gap -= 10; // Reduce the gap gradually
      }
    }
  }

  // Draw foreground
  context.drawImage(fg, 0, canvas.height - fg.height);

  // Bird mechanics
  velocity += gravity; // Apply gravity to velocity
  bY += velocity; // Apply velocity to bird's position

  // Draw bird
  context.drawImage(bird, bX, bY);

  // Display score
  context.fillStyle = "#000";
  context.font = "20px Arial";
  context.fillText("Score : " + score, 10, canvas.height - 20);

  requestAnimationFrame(draw);
}

draw();
