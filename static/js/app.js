document.addEventListener("DOMContentLoaded", () => {
  const date = document.querySelector('input[type="date"]');
  if (date && !date.value) {
    const now = new Date();
    const offset = now.getTimezoneOffset();
    date.value = new Date(now.getTime() - offset*60000).toISOString().slice(0,10);
  }
  document.querySelectorAll(".flash").forEach(el => {
    setTimeout(() => el.classList.add("hide"), 4500);
  });
});

function useLocation() {
  const status = document.getElementById("location-status");
  const input = document.getElementById("location");
  if (!navigator.geolocation) {
    status.textContent = "Geolocation is not supported by this browser.";
    return;
  }
  status.textContent = "Getting your location…";
  navigator.geolocation.getCurrentPosition(
    pos => {
      const {latitude, longitude} = pos.coords;
      input.value = `GPS: ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
      status.textContent = "✓ Current coordinates added. For a production version, reverse-geocode them into an address.";
    },
    () => status.textContent = "Unable to access your location. Please enter the pickup address manually."
  );
}
