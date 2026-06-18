/**
 * chatkhu 크레딧 소진 시뮬레이션 - 차트 추가 스크립트
 *
 * 실행 방법:
 * 1. https://script.google.com 접속 (hahyunkim@khu.ac.kr 계정)
 * 2. 좌측 상단 "새 프로젝트" 클릭
 * 3. 기본 코드 전체 지우고 이 파일 내용 붙여넣기
 * 4. 상단 함수 선택 드롭다운에서 "addCharts" 선택
 * 5. ▶ 실행 버튼 클릭
 * 6. 권한 요청 팝업 → "권한 검토" → 계정 선택 → "허용"
 */

var SPREADSHEET_ID = '1uJmPUHpxsbMn4YFOnCc0tTmKlUaHjC2ViUuApC7PXFE';

function addCharts() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  addCumulativeBurnChart(ss);
  addMonthlyBurnChart(ss);
  SpreadsheetApp.flush();
  Logger.log('차트 2개 추가 완료!');
}

/**
 * 차트 1: 누적 크레딧 소진 꺾은선 차트 (시나리오 A/B/C)
 * - 초록(A 절약형) / 파랑(B 현상유지) / 빨강(C 가속형)
 * - 실적 구간(3~5월) + 예측 구간(6~11월) 연결
 * - N열 2행부터 배치
 */
function addCumulativeBurnChart(ss) {
  var sheet = ss.getSheetByName('시뮬레이션');

  var chartBuilder = sheet.newChart()
    .setChartType(Charts.ChartType.LINE)
    .setPosition(2, 14, 0, 0)
    .setOption('title', '누적 크레딧 소진 예측 (시나리오별)')
    .setOption('titleTextStyle', { fontSize: 13, bold: true, color: '#1a3a5c' })
    .setOption('width', 700)
    .setOption('height', 400)
    .setOption('legend', { position: 'bottom' })
    .setOption('hAxis', { title: '월', slantedText: true, slantedTextAngle: 30 })
    .setOption('vAxis', {
      title: '누적 소진 크레딧',
      format: '#,##0',
      viewWindow: { min: 0, max: 40000000 }
    })
    .setOption('colors', ['#4CAF50', '#2196F3', '#F44336'])
    // 실적 구간: 행 20(헤더) + 21~23(3~5월)
    .addRange(sheet.getRange('A20:A23'))
    .addRange(sheet.getRange('E20:E23'))
    .addRange(sheet.getRange('H20:H23'))
    .addRange(sheet.getRange('K20:K23'))
    // 예측 구간: 행 25~30(6~11월) — 24행 구분선 제외
    .addRange(sheet.getRange('A25:A30'))
    .addRange(sheet.getRange('E25:E30'))
    .addRange(sheet.getRange('H25:H30'))
    .addRange(sheet.getRange('K25:K30'))
    .setNumHeaders(1);

  sheet.insertChart(chartBuilder.build());
  Logger.log('차트 1 (누적 소진 꺾은선) 추가 완료');
}

/**
 * 차트 2: 월별 크레딧 소진량 막대 차트 (시나리오 A/B/C 비교)
 * - 초록(A 절약형) / 파랑(B 현상유지) / 빨강(C 가속형)
 * - N열 24행부터 배치 (차트1 아래)
 */
function addMonthlyBurnChart(ss) {
  var sheet = ss.getSheetByName('시뮬레이션');

  var chartBuilder = sheet.newChart()
    .setChartType(Charts.ChartType.COLUMN)
    .setPosition(24, 14, 0, 0)
    .setOption('title', '월별 크레딧 소진량 비교 (시나리오별)')
    .setOption('titleTextStyle', { fontSize: 13, bold: true, color: '#1a3a5c' })
    .setOption('width', 700)
    .setOption('height', 400)
    .setOption('legend', { position: 'bottom' })
    .setOption('hAxis', { title: '월', slantedText: true, slantedTextAngle: 30 })
    .setOption('vAxis', { title: '월 소진 크레딧', format: '#,##0' })
    .setOption('colors', ['#4CAF50', '#2196F3', '#F44336'])
    // 실적 구간
    .addRange(sheet.getRange('A20:A23'))
    .addRange(sheet.getRange('D20:D23'))
    .addRange(sheet.getRange('G20:G23'))
    .addRange(sheet.getRange('J20:J23'))
    // 예측 구간
    .addRange(sheet.getRange('A25:A30'))
    .addRange(sheet.getRange('D25:D30'))
    .addRange(sheet.getRange('G25:G30'))
    .addRange(sheet.getRange('J25:J30'))
    .setNumHeaders(1);

  sheet.insertChart(chartBuilder.build());
  Logger.log('차트 2 (월별 소진 막대) 추가 완료');
}
