// FoodBridge Interactive Client JS

document.addEventListener('DOMContentLoaded', () => {
  // Auto dismiss flash alerts after 5 seconds
  const flashAlerts = document.querySelectorAll('#flash-container .alert');
  flashAlerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Enable Bootstrap tooltips if any
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
});
