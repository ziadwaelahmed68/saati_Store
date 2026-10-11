// Put your backend URL here (no trailing slash), e.g. "https://api.yourdomain.com"
// Leave it empty to run in demo mode (data saved in the browser only).
// يتم سحب رابط الـ API من متغيرات البيئة (Environment Variables/Secrets) ديناميكياً
window.SAATI_API = window.env?.API_URL || process.env?.REACT_APP_API_URL || "";
// إعدادات AWS Cognito
window.COGNITO_CONFIG = {
    region: "eu-central-1",
    userPoolId: "eu-central-1_61kHuKfU3",
    clientId: "6njag5ke4ps7sar3ecp31r1h4v"
};