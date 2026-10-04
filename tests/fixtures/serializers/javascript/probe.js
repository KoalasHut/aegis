const observed = {
  stack: "JavaScript",
  runtime: process.version,
  library: "ECMAScript JSON/Date",
  options: "JSON.stringify and Date.prototype.toISOString defaults",
  observed: {
    datetime: new Date("2026-10-02T09:00:00Z").toISOString(),
    decimalNumber: JSON.parse(JSON.stringify(10.50)),
    unsafeInteger: JSON.parse(JSON.stringify(9007199254740993)),
    nullAndUndefined: JSON.parse(JSON.stringify({note: null, omitted: undefined})),
  },
};
console.log(JSON.stringify(observed));
