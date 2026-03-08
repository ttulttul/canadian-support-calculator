const path = require('node:path')
const process = require('node:process')

const { notarize } = require('@electron/notarize')

module.exports = async function notarizeApp(context) {
  const { electronPlatformName, appOutDir, packager } = context
  if (electronPlatformName !== 'darwin') {
    return
  }

  const appleId = process.env.APPLE_ID
  const applePassword = process.env.APPLE_APP_SPECIFIC_PASSWORD
  const appleTeamId = process.env.APPLE_TEAM_ID
  if (!appleId || !applePassword || !appleTeamId) {
    console.log('Skipping notarization because Apple credentials are not configured.')
    return
  }

  const appName = packager.appInfo.productFilename
  await notarize({
    appPath: path.join(appOutDir, `${appName}.app`),
    appleId,
    appleIdPassword: applePassword,
    teamId: appleTeamId,
  })
}
