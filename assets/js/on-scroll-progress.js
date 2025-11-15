document.addEventListener('scroll', _ => {
  var docElem = document.documentElement;
  var docBody = document.body;
  var scrollTop = (docBody.scrollTop || docElem.scrollTop);
  var height = docElem.scrollHeight - docElem.clientHeight;

  var progress = scrollTop / height * 100;
  var progressBar = document.querySelector('#progress-bar');
  
  if (!progressBar) return;

  if (progress > 0) {
    progressBar.style.setProperty('--progress', progress + '%');
  } else {
    progressBar.style.setProperty('--progress', '0%');
  }
});

