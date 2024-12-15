var dagfuncs = window.dashAgGridFunctions = window.dashAgGridFunctions || {};

dagfuncs.FileSize = function(number) {
  return Intl.NumberFormat("en", {notation:"compact", style:"unit", unit:"byte", unitDisplay:"narrow"}).format(number).replace("BB", "GB");
}
