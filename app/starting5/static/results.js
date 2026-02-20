$(function () {

    function setupShare(btn, confirm) {
      $(btn).on('click', function () {
        navigator.clipboard.writeText(shareMessage).then(() => {
          fetch('/record_share', { method: 'POST' }).then(() => {
            $(confirm)
              .fadeIn()
              .delay(5000)
              .fadeOut(() => {
                window.location.href = '/quiz?bonus=1';
              });
          });
        });
      });
    }
  
    setupShare('#share-btn', '#share-confirm');
    setupShare('#share-btn-lb', '#share-confirm-lb');
  
    const $scoreLine = $('.score-line');
    const $resultsShare = $('#results-share');
    const $viewLink = $('#view-leaderboard');
  
    $('#view-leaderboard').on('click', function (e) {
      e.preventDefault();
      const $cards = $('#results-cards .result-card');
      $cards.each(function () {
        this.offsetWidth; // reflow
        $(this).addClass('reverse');
      });
      setTimeout(() => {
        $('#results-cards').hide();
        $scoreLine.hide();
        $resultsShare.hide();
        $viewLink.hide();
        $('#results-leaderboard').fadeIn();
        $cards.removeClass('reverse');
      }, 400);
    });
  
    $('#back-answers').on('click', function (e) {
      e.preventDefault();
      $('#results-leaderboard').fadeOut(200, function () {
        const $wrap = $('#results-cards');
        const $cards = $wrap.find('.result-card');
        $wrap.show();
        $scoreLine.show();
        $resultsShare.show();
        $viewLink.show();
        $cards.each(function (i) {
          const delay = i * 0.2;
          const infoDelay = delay + 0.4;
          $(this).css('animation', `pack-drop 0.3s ease forwards ${delay}s`);
          $(this).find('.result-info').css('animation', `pulse-in 0.4s ease forwards ${infoDelay}s`);
        });
      });
    });

    $('#view-past-quizzes').on('click', function (e) {
      e.preventDefault();
      if (!isAuthenticated) {
        window.location.href = loginUrl;
        return;
      }

      const $list = $('#archive-list').empty();
      archiveQuizzes.forEach((q) => {
        $('<li>')
          .append(
            $('<a>')
              .attr('href', '/archive/' + encodeURIComponent(q.id))
              .text(q.label)
          )
          .appendTo($list);
      });

      $('#archive-modal').fadeIn();
    });

    $('#close-archive').on('click', function (e) {
      e.preventDefault();
      $('#archive-modal').fadeOut();
    });
  });
