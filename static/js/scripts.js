function showLoader() {
            document.getElementById('loader').style.display = 'block';
    }

    function hideLoader() {
        document.getElementById('loader').style.display = 'none';
    }

    window.onload = function() {
        // Hide loader on page load (when results are shown)
        hideLoader();
    }
