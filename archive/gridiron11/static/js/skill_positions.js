/* ═══════════════════════════════════════════════════════════════════════════
   NFL Skill Positions - Flashcard Game Logic
   ════════════════════════════════════════════════════════════════════════════ */

class SkillPositionsGame {
  constructor() {
    this.gameData = window.gameData || {};
    this.colleges = window.colleges || [];
    this.players = this.gameData.players || [];
    this.currentIndex = 0;
    this.userAnswers = {};
    this.isSubmitted = false;
    this.cardFlipped = false;
    
    // Touch/swipe handling
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.isSwiping = false;
    this.hasInteracted = false;
    
    // Flag to prevent redundant saves during player switching
    this.isLoadingPlayer = false;
    
    this.init();
  }

  init() {
    this.setupProgressSegments();
    this.setupCollegeSelect();
    this.setupEventListeners();
    this.showCurrentPlayer();
    this.updateProgressSegments();
  }

  setupProgressSegments() {
    const progressContainer = document.getElementById('progressSegments');
    if (!progressContainer) return;
    
    progressContainer.innerHTML = '';
    
    for (let i = 0; i < this.players.length; i++) {
      const segment = document.createElement('div');
      segment.className = 'progress-segment';
      segment.dataset.index = i;
      progressContainer.appendChild(segment);
    }
  }

  setupCollegeSelect(filterByConference = null) {
    const select = document.getElementById('collegeSelectMain');
    if (!select) return;
    
    // Clear existing options except the first one
    select.innerHTML = '<option value="">Select a college...</option>';
    
    // Filter colleges by conference if specified
    let collegesToShow = this.colleges;
    if (filterByConference) {
      collegesToShow = this.colleges.filter(college => {
        const collegeConference = college.conference || this.getCollegeConference(college.name || college);
        return collegeConference && collegeConference.toLowerCase() === filterByConference.toLowerCase();
      });
    }
    
    // Add college options
    collegesToShow.forEach(college => {
      const option = document.createElement('option');
      option.value = college.name || college;
      option.textContent = college.name || college;
      select.appendChild(option);
    });
    
    // Destroy existing Select2 instance if it exists
    if (typeof $ !== 'undefined' && $.fn.select2) {
      if ($(select).hasClass('select2-hidden-accessible')) {
        $(select).select2('destroy');
      }
      
      // Initialize Select2
      $(select).select2({
        placeholder: filterByConference ? 
          `Select a college from ${filterByConference}...` : 
          'Select a college...',
        allowClear: true,
        width: '100%'
      });
    }
  }

  setupEventListeners() {
    // Navigation arrows
    const navLeft = document.getElementById('navLeft');
    const navRight = document.getElementById('navRight');
    
    if (navLeft) {
      navLeft.addEventListener('click', () => this.previousPlayer());
    }
    
    if (navRight) {
      navRight.addEventListener('click', () => this.nextPlayer());
    }
    
    // Action buttons
    const hintBtn = document.getElementById('hintBtn');
    const randomBtn = document.getElementById('randomBtn');
    const submitBtn = document.getElementById('submitBtn');
    
    if (hintBtn) {
      hintBtn.addEventListener('click', () => this.showHint());
    }
    
    if (randomBtn) {
      randomBtn.addEventListener('click', () => this.randomGuess());
    }
    
    if (submitBtn) {
      submitBtn.addEventListener('click', () => this.submitGuess());
    }
    
    // College select change
    const collegeSelect = document.getElementById('collegeSelectMain');
    if (collegeSelect) {
      collegeSelect.addEventListener('change', () => {
        this.saveCurrentAnswer();
        // Note: saveCurrentAnswer() already calls updateSubmitButton()
      });
    }
    
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        this.previousPlayer();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        this.nextPlayer();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        this.submitGuess();
      }
    });
    
    // Touch/swipe events for mobile
    const flashcard = document.getElementById('flashcard');
    if (flashcard) {
      flashcard.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
      flashcard.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: true });
      flashcard.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
    }
    
    // Prevent flashcard click when flipped
    flashcard?.addEventListener('click', (e) => {
      if (this.cardFlipped) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  showCurrentPlayer() {
    const player = this.players[this.currentIndex];
    if (!player) return;
    
    console.log(`🎯 showCurrentPlayer - Loading player ${this.currentIndex + 1}: ${player.name}`);
    this.isLoadingPlayer = true;
    
    // Update player info
    const playerName = document.getElementById('playerName');
    const playerPosition = document.getElementById('playerPosition');
    const playerArt = document.getElementById('playerArt');
    const playerStats = document.getElementById('playerStats');
    
    if (playerName) {
      playerName.textContent = player.name;
    }
    
    if (playerPosition) {
      playerPosition.textContent = player.position;
    }
    
    if (playerArt && player.team_abbrev && player.avatar) {
      const spritePath = `/gridiron11/sprites/${player.team_abbrev}/images/${player.team_abbrev.toLowerCase()}_${player.avatar}.png`;
      console.log(`🎨 Loading sprite for ${player.name}: ${spritePath}`);
      playerArt.src = spritePath;
      playerArt.alt = player.name;
      
      // Add error handling for sprite loading
      playerArt.onerror = function() {
        console.error(`❌ Failed to load sprite: ${spritePath}`);
        console.log(`Team: ${player.team_abbrev}, Avatar: ${player.avatar}`);
      };
      
      playerArt.onload = function() {
        console.log(`✅ Successfully loaded sprite: ${spritePath}`);
      };
    }
    
    if (playerStats) {
      const stats = this.generateMockStats();
      playerStats.innerHTML = `
        <span class="stat">REC: ${stats.receptions}</span>
        <span class="stat">YDS: ${stats.yards}</span>
        <span class="stat">TDS: ${stats.touchdowns}</span>
      `;
    }
    
    // Reset card state
    this.resetCard();
    
    // Reset college dropdown to show all colleges (remove any conference filter)
    this.setupCollegeSelect();
    
    // Load previous answer if exists
    const previousAnswer = this.userAnswers[player.name];
    const collegeSelect = document.getElementById('collegeSelectMain');
    
    console.log(`🔍 Loading previous answer for ${player.name}: "${previousAnswer || 'none'}"`);
    
    if (collegeSelect && previousAnswer) {
      collegeSelect.value = previousAnswer;
      if (typeof $ !== 'undefined' && $.fn.select2) {
        $(collegeSelect).val(previousAnswer).trigger('change');
      }
    } else if (collegeSelect) {
      collegeSelect.value = '';
      if (typeof $ !== 'undefined' && $.fn.select2) {
        $(collegeSelect).val('').trigger('change');
      }
    }
    
    this.isLoadingPlayer = false;
    this.updateSubmitButton();
    this.updateNavigationButtons();
    
    console.log(`✅ showCurrentPlayer complete for ${player.name}`);
  }

  generateMockStats() {
    // Generate realistic NFL stats for skill positions
    const position = this.players[this.currentIndex]?.position || 'WR';
    const basePosition = position.replace(/\d+$/, ''); // Remove numbers (WR1 -> WR)
    
    switch (basePosition) {
      case 'QB':
        return {
          receptions: Math.floor(Math.random() * 5),
          yards: Math.floor(Math.random() * 4500) + 2000,
          touchdowns: Math.floor(Math.random() * 35) + 15
        };
      case 'RB':
        return {
          receptions: Math.floor(Math.random() * 80) + 20,
          yards: Math.floor(Math.random() * 1500) + 500,
          touchdowns: Math.floor(Math.random() * 15) + 3
        };
      case 'WR':
        return {
          receptions: Math.floor(Math.random() * 100) + 40,
          yards: Math.floor(Math.random() * 1500) + 600,
          touchdowns: Math.floor(Math.random() * 12) + 3
        };
      case 'TE':
        return {
          receptions: Math.floor(Math.random() * 70) + 30,
          yards: Math.floor(Math.random() * 800) + 400,
          touchdowns: Math.floor(Math.random() * 10) + 2
        };
      default:
        return {
          receptions: Math.floor(Math.random() * 50) + 20,
          yards: Math.floor(Math.random() * 800) + 300,
          touchdowns: Math.floor(Math.random() * 8) + 2
        };
    }
  }

  updateProgressSegments() {
    const segments = document.querySelectorAll('.progress-segment');
    
    segments.forEach((segment, index) => {
      const player = this.players[index];
      segment.classList.remove('completed', 'current', 'answered');
      
      const hasAnswer = player && this.userAnswers[player.name];
      
      if (index < this.currentIndex) {
        segment.classList.add('completed');
      } else if (index === this.currentIndex) {
        segment.classList.add('current');
      }
      
      if (hasAnswer) {
        segment.classList.add('answered');
      }
    });
  }

  updateNavigationButtons() {
    const navLeft = document.getElementById('navLeft');
    const navRight = document.getElementById('navRight');
    
    if (navLeft) {
      navLeft.disabled = this.currentIndex === 0;
    }
    
    if (navRight) {
      navRight.disabled = this.currentIndex === this.players.length - 1;
    }
  }

  updateSubmitButton() {
    const submitBtn = document.getElementById('submitBtn');
    
    if (submitBtn) {
      // Check if all questions are answered
      const allAnswered = this.players.every(player => this.userAnswers[player.name]);
      
      // Debug logging
      console.log('Submit button update:');
      console.log('- Total players:', this.players.length);
      console.log('- User answers:', Object.keys(this.userAnswers).length);
      console.log('- All answered:', allAnswered);
      console.log('- User answers object:', this.userAnswers);
      
      if (allAnswered) {
        submitBtn.textContent = 'Submit All Answers';
        submitBtn.disabled = false;
        console.log('- Button enabled ✅');
      } else {
        submitBtn.textContent = 'Submit All Answers';
        submitBtn.disabled = true;
        console.log('- Button disabled ❌');
        
        // Show which players are missing answers
        const missingAnswers = this.players.filter(player => !this.userAnswers[player.name]);
        console.log('- Missing answers for:', missingAnswers.map(p => p.name));
      }
    }
  }

  resetCard() {
    const flashcard = document.getElementById('flashcard');
    if (flashcard) {
      flashcard.classList.remove('flipped', 'correct', 'wrong');
      this.cardFlipped = false;
    }
    this.updateSubmitButton();
  }

  previousPlayer() {
    this.hideMobileHint();
    // Save current answer before moving
    this.saveCurrentAnswer();
    
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.showCurrentPlayer();
      this.updateProgressSegments();
    }
  }

  nextPlayer() {
    this.hideMobileHint();
    // Save current answer before moving
    this.saveCurrentAnswer();
    
    if (this.currentIndex < this.players.length - 1) {
      this.currentIndex++;
      this.showCurrentPlayer();
      this.updateProgressSegments();
    }
    // Don't auto-submit anymore - user must use "Submit All Answers" button
  }

  hideMobileHint() {
    if (!this.hasInteracted) {
      this.hasInteracted = true;
      const mobileHint = document.getElementById('mobileHint');
      if (mobileHint) {
        mobileHint.style.opacity = '0';
        setTimeout(() => {
          mobileHint.style.display = 'none';
        }, 300);
      }
    }
  }

  saveCurrentAnswer() {
    const collegeSelect = document.getElementById('collegeSelectMain');
    const player = this.players[this.currentIndex];
    
    console.log(`🔄 saveCurrentAnswer called - Current player: ${player?.name}, Current index: ${this.currentIndex}, isLoadingPlayer: ${this.isLoadingPlayer}`);
    
    if (!collegeSelect || !player) {
      console.log('❌ Missing collegeSelect or player, returning early');
      return;
    }
    
    // Skip saving if we're just loading the player (to avoid overwriting with old values)
    if (this.isLoadingPlayer) {
      console.log('⏭️ Skipping save - currently loading player');
      return;
    }
    
    const answer = collegeSelect.value.trim();
    console.log(`📝 Dropdown value: "${answer}"`);
    
    if (answer) {
      this.userAnswers[player.name] = answer;
      console.log(`✅ Auto-saved answer for ${player.name}: ${answer}`);
    } else if (this.userAnswers[player.name]) {
      // If dropdown is cleared, remove the saved answer
      delete this.userAnswers[player.name];
      console.log(`🗑️ Removed answer for ${player.name}`);
    } else {
      console.log(`📭 No answer to save for ${player.name}`);
    }
    
    this.updateProgressSegments();
    this.updateSubmitButton();
  }

  submitGuess() {
    // Save current answer first
    this.saveCurrentAnswer();
    
    // Check if all questions are answered
    const allAnswered = this.players.every(player => this.userAnswers[player.name]);
    
    if (!allAnswered) {
      this.showIncompleteWarning();
      return;
    }
    
    // All questions answered - show final results
    this.showFinalResults();
  }


  showHint() {
    const player = this.players[this.currentIndex];
    if (!player) return;
    
    const college = player.college;
    const conference = this.getCollegeConference(college);
    
    this.showHintModal(college, conference);
    
    // Filter the dropdown to only show colleges from this conference
    this.setupCollegeSelect(conference);
  }

  getCollegeConference(collegeName) {
    // Find the conference for this college
    const collegeData = this.colleges.find(c => 
      (c.name && c.name.toLowerCase() === collegeName.toLowerCase()) ||
      (typeof c === 'string' && c.toLowerCase() === collegeName.toLowerCase())
    );
    
    if (collegeData && collegeData.conference) {
      return collegeData.conference;
    }
    
    // Fallback - try to match college name variations
    const normalizedName = collegeName.toLowerCase();
    const matchedCollege = this.colleges.find(c => {
      const name = (c.name || c).toLowerCase();
      return name.includes(normalizedName) || normalizedName.includes(name);
    });
    
    return matchedCollege?.conference || 'Unknown Conference';
  }

  showHintModal(college, conference) {
    // Create hint modal if it doesn't exist
    let hintModal = document.getElementById('hintModal');
    if (!hintModal) {
      hintModal = document.createElement('div');
      hintModal.id = 'hintModal';
      hintModal.className = 'modal';
      hintModal.innerHTML = `
        <div class="modal-backdrop" id="hintBackdrop"></div>
        <div class="modal-panel hint-modal-panel">
          <div class="hint-modal-header">
            <h3>💡 Hint</h3>
            <button class="hint-close-btn" id="hintCloseBtn">×</button>
          </div>
          <div class="hint-modal-content">
            <div class="hint-conference">
              <strong>Conference:</strong>
              <span id="hintConference">${conference}</span>
            </div>
            <div class="hint-text">
              This player attended a school in the <strong>${conference}</strong>
            </div>
            <div class="hint-filter-info">
              🎯 The dropdown has been filtered to only show <strong>${conference}</strong> schools!
            </div>
            <div class="hint-actions">
              <button class="show-all-colleges-btn" id="showAllCollegesBtn">Show All Colleges</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(hintModal);
      
      // Add event listeners
      const backdrop = hintModal.querySelector('#hintBackdrop');
      const closeBtn = hintModal.querySelector('#hintCloseBtn');
      
      [backdrop, closeBtn].forEach(element => {
        element.addEventListener('click', () => {
          hintModal.classList.remove('show');
        });
      });
      
      // Add show all colleges button listener
      const showAllBtn = hintModal.querySelector('#showAllCollegesBtn');
      if (showAllBtn) {
        showAllBtn.addEventListener('click', () => {
          this.setupCollegeSelect(); // Reset to show all colleges
          hintModal.classList.remove('show');
        });
      }
    }
    
    // Update content and show
    const conferenceSpan = hintModal.querySelector('#hintConference');
    const hintText = hintModal.querySelector('.hint-text');
    const filterInfo = hintModal.querySelector('.hint-filter-info');
    
    if (conferenceSpan) {
      conferenceSpan.textContent = conference;
    }
    
    if (hintText) {
      hintText.innerHTML = `This player attended a school in the <strong>${conference}</strong>`;
    }
    
    if (filterInfo) {
      filterInfo.innerHTML = `🎯 The dropdown has been filtered to only show <strong>${conference}</strong> schools!`;
    }
    
    hintModal.classList.add('show');
  }

  showIncompleteWarning() {
    const unansweredPlayers = this.players.filter(player => !this.userAnswers[player.name]);
    const playerNames = unansweredPlayers.map(p => p.name).join(', ');
    
    alert(`Please answer all questions before finishing!\n\nMissing answers for: ${playerNames}`);
  }

  randomGuess() {
    const collegeSelect = document.getElementById('collegeSelectMain');
    if (!collegeSelect || this.colleges.length === 0) return;
    
    const randomCollege = this.colleges[Math.floor(Math.random() * this.colleges.length)];
    const collegeName = randomCollege.name || randomCollege;
    
    collegeSelect.value = collegeName;
    if (typeof $ !== 'undefined' && $.fn.select2) {
      $(collegeSelect).val(collegeName).trigger('change');
    }
    
    this.updateSubmitButton();
  }

  // Touch/Swipe handling for mobile
  handleTouchStart(e) {
    this.touchStartX = e.touches[0].clientX;
    this.touchStartY = e.touches[0].clientY;
    this.isSwiping = false;
  }

  handleTouchMove(e) {
    if (!this.touchStartX || !this.touchStartY) return;
    
    const touchX = e.touches[0].clientX;
    const touchY = e.touches[0].clientY;
    
    const diffX = this.touchStartX - touchX;
    const diffY = this.touchStartY - touchY;
    
    // Check if it's a horizontal swipe (not vertical scroll)
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 30) {
      this.isSwiping = true;
    }
  }

  handleTouchEnd(e) {
    if (!this.touchStartX || !this.touchStartY || !this.isSwiping) {
      this.touchStartX = 0;
      this.touchStartY = 0;
      this.isSwiping = false;
      return;
    }
    
    const touchEndX = e.changedTouches[0].clientX;
    const diffX = this.touchStartX - touchEndX;
    
    // Minimum swipe distance
    if (Math.abs(diffX) > 50) {
      if (diffX > 0) {
        // Swiped left - next player
        this.nextPlayer();
      } else {
        // Swiped right - previous player
        this.previousPlayer();
      }
    }
    
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.isSwiping = false;
  }

  showFinalResults() {
    // Calculate final score
    let correctCount = 0;
    const playerResults = [];
    
    this.players.forEach(player => {
      const userAnswer = this.userAnswers[player.name];
      const isCorrect = userAnswer && userAnswer.toLowerCase() === player.college.toLowerCase();
      
      if (isCorrect) {
        correctCount++;
      }
      
      playerResults.push({
        name: player.name,
        position: player.position,
        correct_answer: player.college,
        user_answer: userAnswer || 'No answer',
        is_correct: isCorrect
      });
    });
    
    // Submit score to backend
    this.submitScore(correctCount, this.players.length, playerResults);
    
    // Prepare data for results page
    const resultsData = {
      players: this.players.map(player => ({
        name: player.name,
        position: player.position,
        team_abbrev: player.team_abbrev,
        avatar: player.avatar
      })),
      results: playerResults,
      score: correctCount,
      total_players: this.players.length
    };
    
    // Encode data and redirect to results page
    const encodedData = btoa(JSON.stringify(resultsData));
    window.location.href = `/gridiron11/results?data=${encodedData}`;
  }

  async submitScore(score, total, playerResults) {
    // Only submit if there's game data (not guest mode)
    if (!this.gameData || !this.gameData.quiz_file) {
      console.log('No quiz data available, skipping score submission');
      return;
    }

    try {
      const response = await fetch('/gridiron11/api/submit_skill_positions_score', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          score: score,
          total: total,
          quiz_file: this.gameData.quiz_file,
          time_taken: null, // We could add a timer later
          player_results: playerResults
        })
      });

      const result = await response.json();
      
      if (result.success) {
        console.log('Score saved successfully!');
      } else if (result.message === 'Login required to save scores') {
        console.log('User not logged in, score not saved');
      } else {
        console.log('Failed to save score:', result.error || result.message);
      }
      
    } catch (error) {
      console.error('Error submitting score:', error);
    }
  }

  generateResultsHTML() {
    let html = '<div class="results-cards-container">';
    
    this.players.forEach((player, index) => {
      const userAnswer = this.userAnswers[player.name] || 'No answer';
      const isCorrect = userAnswer.toLowerCase() === player.college.toLowerCase();
      const conference = this.getCollegeConference(player.college);
      
      const spritePath = `/gridiron11/sprites/${player.team_abbrev}/images/${player.team_abbrev.toLowerCase()}_${player.avatar}.png`;
      console.log(`🎨 Results sprite for ${player.name}: ${spritePath}`);
      
      html += `
        <div class="result-card ${isCorrect ? 'correct' : 'wrong'}">
          <div class="result-card-header">
            <div class="result-status">
              ${isCorrect ? '✅' : '❌'}
            </div>
          </div>
          
          <div class="result-card-body">
            <div class="result-player-image">
              <img src="${spritePath}" alt="${player.name}" class="result-player-art" 
                   onerror="console.error('❌ Failed to load results sprite:', '${spritePath}')"
                   onload="console.log('✅ Loaded results sprite:', '${spritePath}')">
            </div>
            
            <div class="result-player-info">
              <h3 class="result-player-name">${player.name}</h3>
              <span class="result-player-position">${player.position}</span>
            </div>
            
            <div class="result-answer-section">
              ${isCorrect ? `
                <div class="result-correct-answer">
                  <div class="correct-college">${player.college}</div>
                  <div class="correct-conference">${conference}</div>
                </div>
              ` : `
                <div class="result-wrong-answers">
                  <div class="your-wrong-answer">
                    <span class="label">Your answer:</span>
                    <span class="wrong-answer-text">${userAnswer}</span>
                  </div>
                  <div class="correct-answer-reveal">
                    <span class="label">Correct:</span>
                    <span class="correct-answer-text">${player.college}</span>
                    <span class="answer-conference">(${conference})</span>
                  </div>
                </div>
              `}
            </div>
          </div>
        </div>
      `;
    });
    
    html += '</div>';
    return html;
  }

  setupModalEvents() {
    const modal = document.getElementById('resultsModal');
    const backdrop = document.getElementById('modalBackdrop');
    const closeBtn = document.getElementById('closeBtn');
    
    [backdrop, closeBtn].forEach(element => {
      if (element) {
        element.addEventListener('click', () => {
          if (modal) {
            modal.classList.remove('show');
          }
        });
      }
    });
  }
}

// Initialize the game when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.game = new SkillPositionsGame();
});