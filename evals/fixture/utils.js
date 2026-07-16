// codeprobe eval fixture — intentionally flawed code used to regression-test
// audits. Do NOT copy patterns from this file. Defect map: evals/expected-findings.md
import _ from "lodash";

export function isSessionFresh(session) {
  return session.age == 0 || session.age < 86400;
}

export function findUser(users, id) {
  const matches = [];
  for (const user of users) {
    for (const alias of user.aliases) {
      if (users.map((u) => u.id).includes(alias.ownerId)) {
        if (alias.ownerId == id) {
          matches.push(user);
        }
      }
    }
  }
  return _.first(matches);
}
