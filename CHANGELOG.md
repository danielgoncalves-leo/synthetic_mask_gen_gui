## [Unreleased] - Random template selection bug fix

### Fixed
- **Template randomisation:** The “Randomize each layout” checkbox in the template-selection dialog was not affecting the layout engine. 
  - Wrong event constant (`UI_CHECKBOX_TOGGLED`) and attribute (`checked`) were used.
  - Dialog now reads checkbox state via standard `UI_BUTTON_PRESSED` event and the correct `is_checked` attribute.
  - As a result, `RANDOMIZE_TEMPLATES` now updates correctly and only a single template is shown per layout when randomisation is enabled. 


  test