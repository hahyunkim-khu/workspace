/**
 * 시뮬레이션 탭 조건부 서식 적용
 *
 * 실행 방법:
 * 1. https://script.google.com 접속 (hahyunkim@khu.ac.kr)
 * 2. 새 프로젝트 → 기존 코드 전체 삭제 후 이 파일 내용 붙여넣기
 * 3. 함수 드롭다운에서 "applyConditionalFormat" 선택 → ▶ 실행
 */

var SPREADSHEET_ID = '1uJmPUHpxsbMn4YFOnCc0tTmKlUaHjC2ViUuApC7PXFE';

function applyConditionalFormat() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheet = ss.getSheetByName('시뮬레이션');

  // 기존 조건부 서식 규칙 유지하면서 추가
  var rules = sheet.getConditionalFormatRules();

  // 잔여 크레딧 열: F(A), I(B), L(C) — 행 24~33
  var rangesNegative = [
    sheet.getRange('F24:F33'),
    sheet.getRange('I24:I33'),
    sheet.getRange('L24:L33')
  ];

  // 음수일 때: 빨간 배경 + 흰 텍스트 + 볼드
  var ruleNegative = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberLessThan(0)
    .setBackground('#C62828')
    .setFontColor('#FFFFFF')
    .setBold(true)
    .setRanges(rangesNegative)
    .build();

  // 0 이상 ~ 5,000,000 미만: 주황 경고
  var ruleWarning = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberBetween(0, 4999999)
    .setBackground('#FF8F00')
    .setFontColor('#FFFFFF')
    .setBold(true)
    .setRanges(rangesNegative)
    .build();

  rules.push(ruleWarning);
  rules.push(ruleNegative);
  sheet.setConditionalFormatRules(rules);

  SpreadsheetApp.flush();
  Logger.log('조건부 서식 적용 완료');
}
