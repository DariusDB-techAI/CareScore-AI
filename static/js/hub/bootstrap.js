export const criteriaConfig = (window.APP_BOOTSTRAP && Array.isArray(window.APP_BOOTSTRAP.criteria))
    ? window.APP_BOOTSTRAP.criteria
    : [];

export const criteriaById = Object.fromEntries(criteriaConfig.map((item) => [item.id, item]));

export function getWsPath() {
    return (window.APP_BOOTSTRAP && window.APP_BOOTSTRAP.wsPath) || "/ws/chat";
}
