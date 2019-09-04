$(document).ready(function(){
    $('#targetbox').keypress(function(e){
      if(e.keyCode==13)
      $('#plot').click();
    });
});
