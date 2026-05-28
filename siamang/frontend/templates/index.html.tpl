<!doctype html>
<html lang="${language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>${title}</title>
  <link rel="preconnect" href="https://unpkg.com" crossorigin>
  <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap">
  <link rel="stylesheet" href="${surveyjs_css}">
  <link rel="stylesheet" href="${css_href}">
</head>
<body>
  <a class="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
  <div id="survey">
    ${header_html}
    ${progress_html}
    <main id="surveyContainer" role="main" aria-label="${title}"></main>
    ${footer_html}
  </div>
  <script src="${surveyjs_js}"></script>
  <script src="${surveyjs_ui}"></script>
  <script src="${env_src}"></script>
  <script>
    (function() {
      const schema = ${schema_json};
      const SurveyCore = window.Survey || window.SurveyCore;
      if (!SurveyCore || typeof SurveyCore.Model !== "function") {
        console.error("siamang: survey-core failed to load from CDN.");
        return;
      }
      const survey = new SurveyCore.Model(schema);

      const transportName = (window.SIAMANG_ENV && window.SIAMANG_ENV.transport) || "noop";
      const transport = (window.SIAMANG_TRANSPORTS || {})[transportName];

      const container = document.getElementById("surveyContainer");
      const progressFill = document.getElementById("siamang-progress-fill");
      const progressText = document.getElementById("siamang-progress-text");

      function updateProgress(sender) {
        if (!progressFill && !progressText) return;
        const total = sender.visiblePageCount || sender.pageCount || sender.PageCount || 1;
        const current = (sender.currentPageNo || 0) + 1;
        const ratio = total > 0 ? Math.min(100, Math.round(current / total * 100)) : 0;
        if (progressFill) progressFill.style.width = ratio + "%";
        if (progressText) progressText.textContent = "Page " + current + " of " + total;
      }
      survey.onCurrentPageChanged.add(updateProgress);
      survey.onStarted.add(updateProgress);

      /**
       * Flatten nested objects (e.g. SurveyJS matrix responses) into
       * dot-separated top-level keys.
       *
       * Example: { matrix_q: { row1: 3, row2: 4 } }
       *       -> { "matrix_q.row1": 3, "matrix_q.row2": 4 }
       */
      function flattenResponses(data) {
        const result = {};
        for (const [key, value] of Object.entries(data)) {
          if (value !== null && typeof value === "object" && !Array.isArray(value)) {
            for (const [subKey, subVal] of Object.entries(value)) {
              result[key + "." + subKey] = subVal;
            }
          } else {
            result[key] = value;
          }
        }
        return result;
      }

      survey.onComplete.add(async function(sender) {
        const responses = flattenResponses(sender.data);
        if (transport && typeof transport.submit === "function") {
          try {
            await transport.submit(responses);
          } catch (err) {
            console.error("siamang transport error:", err);
          }
        }
      });

      // SurveyJS 2.x: window.SurveyUI.renderSurvey(model, container)
      if (window.SurveyUI && typeof window.SurveyUI.renderSurvey === "function") {
        window.SurveyUI.renderSurvey(survey, container);
      } else if (window.SurveyJS && window.SurveyJS.SurveyUI &&
                 typeof window.SurveyJS.SurveyUI.renderSurvey === "function") {
        window.SurveyJS.SurveyUI.renderSurvey(survey, container);
      } else if (window.SurveyJSUI && typeof window.SurveyJSUI.renderSurvey === "function") {
        window.SurveyJSUI.renderSurvey(survey, container);
      } else {
        console.error("siamang: survey-js-ui renderer not found on window.");
      }
      updateProgress(survey);
    })();
  </script>
</body>
</html>
