const HOURHAND1 = document.querySelector("#hour1"); // Target hour hand in clock 1 svg
const MINUTEHAND1 = document.querySelector("#minute1"); // Target minute hand in clock 1 svg
const SECONDHAND1 = document.querySelector("#second1"); // Target second hand in clock 1 svg

const HOURHAND2 = document.querySelector("#hour2"); // Target hour hand in clock 2 svg
const MINUTEHAND2 = document.querySelector("#minute2"); // Target minute hand in clock 2 svg
const SECONDHAND2 = document.querySelector("#second2"); // Target second hand in clock 2 svg

function getLocalTimeZoneAbbreviation(date) {
    try {
        const parts = new Intl.DateTimeFormat(undefined, {
            timeZoneName: "short"
        }).formatToParts(date);
        const tzPart = parts.find((p) => p.type === "timeZoneName");
        return tzPart?.value ?? null;
    } catch {
        return null;
    }
}

function setLocalTimeZoneAbbreviation() {
    const el = document.getElementById("localTzAbbr");
    if (!el) return;

    const now = new Date();
    const abbr = getLocalTimeZoneAbbreviation(now);
    const fallback = Intl.DateTimeFormat().resolvedOptions().timeZone;
    el.textContent = abbr || fallback || "Local";
}

function runClock1() {
    const date1 = new Date(); // Get current date and time for clock 1

    const hr1 = date1.getHours(); // Get current hour for clock 1
    const min1 = date1.getMinutes(); // Get current minute for clock 1
    const sec1 = date1.getSeconds(); // Get current second for clock 1

    const hrPosition1 = (hr1 * 360 / 12) + (min1 * (360 / 60) / 12); // Hour hand degrees for clock 1
    const minPosition1 = (min1 * 360 / 60) + (sec1 * (360 / 60) / 60); // Minute hand degrees for clock 1
    const secPosition1 = sec1 * 360 / 60; // Second hand degrees for clock 1

    HOURHAND1.style.transform = "rotate(" + hrPosition1 + "deg)"; // Position hour hand for clock 1
    MINUTEHAND1.style.transform = "rotate(" + minPosition1 + "deg)"; // Position minute hand for clock 1
    SECONDHAND1.style.transform = "rotate(" + secPosition1 + "deg)"; // Position second hand for clock 1
}

function runClock2() {
    var date2 = new Date(); // Get current date and time for clock 2

    let hr2 = date2.getUTCHours(); // Get UTC current hour for clock 2
    let min2 = date2.getUTCMinutes(); // Get UTC current minute for clock 2
    let sec2 = date2.getUTCSeconds(); // Get UTC current second for clock 2

    let hrPosition2 = (hr2 * 360 / 12) + (min2 * (360 / 60) / 12); // Hour hand degrees for clock 2
    let minPosition2 = (min2 * 360 / 60) + (sec2 * (360 / 60) / 60); // Minute hand degrees for clock 2
    let secPosition2 = sec2 * 360 / 60; // Second hand degrees for clock 2

    HOURHAND2.style.transform = "rotate(" + hrPosition2 + "deg)"; // Position hour hand for clock2
    MINUTEHAND2.style.transform = "rotate(" + minPosition2 + "deg)"; // Position minute hand for clock 2
    SECONDHAND2.style.transform = "rotate(" + secPosition2 + "deg)"; // Position second hand for clock 2

}

runClock1();
runClock2();
setLocalTimeZoneAbbreviation();

const clock1Interval = setInterval(runClock1, 1000); // Run the clock 1 function every second
const clock2Interval = setInterval(runClock2, 1000); // Run the clock 2 function every second