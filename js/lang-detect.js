var langPage, langCodes;

langCodes = {es: 'es'}

if( (langPage = langCodes[ (navigator.language||navigator.userLanguage).substring(0,2) ]) )
 location.replace(langPage+".html")
