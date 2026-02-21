// Skill Positions Results Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // Setup share functionality
  const shareBtn = document.getElementById('share-btn');
  const shareConfirm = document.getElementById('share-confirm');
  
  if (shareBtn) {
    shareBtn.addEventListener('click', function() {
      // Get score from the page
      const scoreLine = document.querySelector('.score-line');
      const scoreText = scoreLine ? scoreLine.textContent : 'Check out my Skill Positions score!';
      
      // Create share text
      const shareText = `🏈 ${scoreText} on Where'd He Go? - Skill Positions Quiz!\n\nCan you beat my score? Play at wheredhego.com`;
      
      // Try to copy to clipboard
      if (navigator.clipboard) {
        navigator.clipboard.writeText(shareText).then(function() {
          showShareConfirmation();
        }).catch(function() {
          fallbackCopyTextToClipboard(shareText);
        });
      } else {
        fallbackCopyTextToClipboard(shareText);
      }
    });
  }
  
  function showShareConfirmation() {
    if (shareConfirm) {
      shareConfirm.style.display = 'inline';
      setTimeout(function() {
        shareConfirm.style.display = 'none';
      }, 2000);
    }
  }
  
  function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.position = 'fixed';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      const successful = document.execCommand('copy');
      if (successful) {
        showShareConfirmation();
      }
    } catch (err) {
      console.error('Fallback: Oops, unable to copy', err);
    }
    
    document.body.removeChild(textArea);
  }
});
