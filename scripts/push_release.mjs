import { execFileSync } from 'node:child_process'
import process from 'node:process'

import semver from 'semver'

const projectRoot = process.cwd()

function run(command, args) {
  execFileSync(command, args, {
    cwd: projectRoot,
    stdio: 'inherit',
  })
}

function runText(command, args) {
  return execFileSync(command, args, {
    cwd: projectRoot,
    encoding: 'utf8',
  }).trim()
}

function main() {
  const version = process.argv[2]
  if (!semver.valid(version)) {
    throw new Error('Usage: npm run release:push -- <semver-version>')
  }

  const branch = runText('git', ['rev-parse', '--abbrev-ref', 'HEAD'])
  if (branch === 'HEAD') {
    throw new Error('Release push requires a branch checkout, not a detached HEAD.')
  }

  run('git', ['rev-parse', '--verify', `refs/tags/v${version}`])
  run('git', ['push', 'origin', branch])
  run('git', ['push', 'origin', `v${version}`])
}

main()
