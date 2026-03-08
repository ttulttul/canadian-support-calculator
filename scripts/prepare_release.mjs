import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'

import semver from 'semver'

const projectRoot = process.cwd()

function run(command, args, options = {}) {
  execFileSync(command, args, {
    cwd: projectRoot,
    stdio: 'inherit',
    ...options,
  })
}

function runText(command, args) {
  return execFileSync(command, args, {
    cwd: projectRoot,
    encoding: 'utf8',
  }).trim()
}

function ensureCleanWorktree() {
  const status = runText('git', ['status', '--porcelain'])
  if (status) {
    throw new Error('Release preparation requires a clean git worktree.')
  }
}

function updateJsonVersion(filePath, version) {
  const absolutePath = path.join(projectRoot, filePath)
  const payload = JSON.parse(fs.readFileSync(absolutePath, 'utf8'))
  payload.version = version
  fs.writeFileSync(absolutePath, `${JSON.stringify(payload, null, 2)}\n`)
}

function updatePyprojectVersion(version) {
  const absolutePath = path.join(projectRoot, 'pyproject.toml')
  const current = fs.readFileSync(absolutePath, 'utf8')
  const updated = current.replace(/^version = ".*"$/m, `version = "${version}"`)
  fs.writeFileSync(absolutePath, updated)
}

function main() {
  const version = process.argv[2]
  if (!semver.valid(version)) {
    throw new Error('Usage: npm run release:prepare -- <semver-version>')
  }

  ensureCleanWorktree()
  updateJsonVersion('package.json', version)
  updateJsonVersion(path.join('frontend', 'package.json'), version)
  updatePyprojectVersion(version)
  run('npm', ['install', '--package-lock-only'])
  run('npm', ['run', 'backend:test'])
  run('npm', ['run', 'frontend:test'])
  run('npm', ['run', 'desktop:test'])
  run('git', ['add', 'package.json', 'package-lock.json', 'frontend/package.json', 'pyproject.toml'])
  run('git', ['commit', '-m', `chore(release): v${version}`])
  run('git', ['tag', '-a', `v${version}`, '-m', `Release v${version}`])
}

main()
