(function($){
  $(function(){

    $('.button-collapse').sideNav()({
        menuWidth: 200, // Default is 240
        edge: 'right', // Choose the horizontal origin
        closeOnClick: true // Closes side-nav on <a> clicks, useful for Angular/Meteor
      }
    );
    $('.parallax').parallax();
    $('ul.tabs').tabs();
    //$('.collapsible').collapsible();

  }); // end of document ready
})(jQuery); // end of jQuery name space
