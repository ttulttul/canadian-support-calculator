import { useEffect, useEffectEvent, useRef, useState } from 'react'
import './App.css'

const defaultScenario = {
  jurisdiction: 'BC',
  children: '2',
  childrenUnderSix: '0',
  taxYear: '2023',
  payorIncome: '244658',
  recipientIncome: '30600',
  useSeparateSpousalIncomes: false,
  payorSpousalIncome: '',
  recipientSpousalIncome: '',
  fixedTotalSupportAnnual: '',
  targetMinPercent: '40',
  targetMaxPercent: '46',
}

const baseTaxYear = 2023
const defaultExtrapolationRate = 0.025
const combinedApproxTaxBrackets2023 = [
  [0, 45654, 20.06],
  [45654, 53359, 22.7],
  [53359, 91310, 28.2],
  [91310, 104835, 31.0],
  [104835, 106717, 32.79],
  [106717, 127299, 38.29],
  [127299, 165430, 40.7],
  [165430, 172602, 44.02],
  [172602, 235675, 46.12],
  [235675, 240716, 49.8],
  [240716, Number.POSITIVE_INFINITY, 53.5],
]
const knownTaxYearIndexFactors = {
  2017: 45916 / 53359,
  2018: 46605 / 53359,
  2019: 47630 / 53359,
  2020: 48535 / 53359,
  2021: 49020 / 53359,
  2022: 50197 / 53359,
  2023: 1,
  2024: 55867 / 53359,
  2025: 57375 / 53359,
}
const ccbChildCountCap = 4
const ccbConfigs = {
  2021: {
    under6: 6997,
    age6To17: 5903,
    threshold1: 32797,
    threshold2: 71060,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 2678, 2: 5166, 3: 7270, 4: 8801 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
  2022: {
    under6: 7437,
    age6To17: 6275,
    threshold1: 34863,
    threshold2: 75537,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 2847, 2: 5490, 3: 7726, 4: 9352 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
  2023: {
    under6: 7787,
    age6To17: 6570,
    threshold1: 36502,
    threshold2: 79087,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 2981, 2: 5749, 3: 8091, 4: 9795 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
  2024: {
    under6: 7997,
    age6To17: 6748,
    threshold1: 37487,
    threshold2: 81222,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 3061, 2: 5904, 3: 8310, 4: 10059 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
}
const gstConfigs = {
  2021: {
    baseCredit: 306,
    childCredit: 161,
    singleSupplement: 161,
    singleSupplementThreshold: 9919,
    phaseoutThreshold: 39826,
  },
  2022: {
    baseCredit: 325,
    childCredit: 171,
    singleSupplement: 171,
    singleSupplementThreshold: 10544,
    phaseoutThreshold: 42335,
  },
  2023: {
    baseCredit: 340,
    childCredit: 179,
    singleSupplement: 179,
    singleSupplementThreshold: 11039,
    phaseoutThreshold: 44324,
  },
  2024: {
    baseCredit: 349,
    childCredit: 184,
    singleSupplement: 184,
    singleSupplementThreshold: 11337,
    phaseoutThreshold: 45521,
  },
}
const bcFamilyBenefitConfigs = {
  2022: {
    maxFirstChild: 1750,
    maxSecondChild: 1100,
    maxAdditionalChild: 900,
    minFirstChild: 775,
    minSecondChild: 750,
    minAdditionalChild: 725,
    maxThreshold: 27354,
    phaseoutThreshold: 87533,
    singleParentSupplement: 500,
  },
  2023: {
    maxFirstChild: 2188,
    maxSecondChild: 1375,
    maxAdditionalChild: 1125,
    minFirstChild: 969,
    minSecondChild: 937,
    minAdditionalChild: 906,
    maxThreshold: 35902,
    phaseoutThreshold: 114887,
    singleParentSupplement: 500,
  },
  2024: {
    maxFirstChild: 1750,
    maxSecondChild: 1100,
    maxAdditionalChild: 900,
    minFirstChild: 775,
    minSecondChild: 750,
    minAdditionalChild: 725,
    maxThreshold: 29526,
    phaseoutThreshold: 94483,
    singleParentSupplement: 500,
  },
}
const bcClimateConfigs = {
  2021: {
    adult: 447,
    secondAdultOrFirstChild: 223.5,
    additionalChild: 111.5,
    singleThreshold: 39115,
    familyThreshold: 50170,
  },
  2022: {
    adult: 504,
    secondAdultOrFirstChild: 252,
    additionalChild: 126,
    singleThreshold: 41071,
    familyThreshold: 57288,
  },
  2023: {
    adult: 504,
    secondAdultOrFirstChild: 252,
    additionalChild: 126,
    singleThreshold: 41071,
    familyThreshold: 57288,
  },
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`
}

function formatSignedCurrency(value) {
  if (value > 0) {
    return `+${formatCurrency(value)}`
  }
  if (value < 0) {
    return `-${formatCurrency(Math.abs(value))}`
  }
  return formatCurrency(0)
}

function asNumber(value, fallback = 0) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback
}

function resolveTaxYearIndexFactor(taxYear) {
  if (taxYear in knownTaxYearIndexFactors) {
    return knownTaxYearIndexFactors[taxYear]
  }

  const knownYears = Object.keys(knownTaxYearIndexFactors).map(Number)
  const minYear = Math.min(...knownYears)
  const maxYear = Math.max(...knownYears)

  if (taxYear < minYear) {
    const years = minYear - taxYear
    return knownTaxYearIndexFactors[minYear] / (1 + defaultExtrapolationRate) ** years
  }

  const years = taxYear - maxYear
  return knownTaxYearIndexFactors[maxYear] * (1 + defaultExtrapolationRate) ** years
}

function calculateApproxBcTax(income, taxYear) {
  const normalizedIncome = Math.max(asNumber(income), 0)
  const factor = resolveTaxYearIndexFactor(taxYear)
  let tax = 0

  for (const [lower, upper, rate] of combinedApproxTaxBrackets2023) {
    const indexedLower = lower * factor
    const indexedUpper = upper === Number.POSITIVE_INFINITY ? upper : upper * factor
    if (normalizedIncome <= indexedLower) {
      break
    }

    const taxableAmount = Math.min(normalizedIncome, indexedUpper) - indexedLower
    tax += taxableAmount * rate / 100
  }

  return Number(tax.toFixed(2))
}

function calculateEquivalentBeforeTaxIncome(targetNetIncome, taxYear) {
  const normalizedTarget = Math.max(asNumber(targetNetIncome), 0)
  if (normalizedTarget <= 0) {
    return 0
  }

  let lower = normalizedTarget
  let upper = Math.max(normalizedTarget, 1)

  while (upper - calculateApproxBcTax(upper, taxYear) < normalizedTarget && upper < 10_000_000) {
    upper *= 2
  }

  for (let index = 0; index < 80; index += 1) {
    const midpoint = (lower + upper) / 2
    const derivedNetIncome = midpoint - calculateApproxBcTax(midpoint, taxYear)

    if (derivedNetIncome < normalizedTarget) {
      lower = midpoint
    } else {
      upper = midpoint
    }
  }

  return Number(upper.toFixed(2))
}

function sanitizeEditableIncomeInput(value) {
  const normalizedValue = String(value).replace(/[^\d.]/g, '')
  const [integerPart = '', ...decimalParts] = normalizedValue.split('.')
  const sanitizedIntegerPart = integerPart.replace(/^0+(?=\d)/, '') || '0'

  if (decimalParts.length === 0) {
    return sanitizedIntegerPart
  }

  return `${sanitizedIntegerPart}.${decimalParts.join('')}`
}

function parseEditableIncome(value) {
  return Number.parseFloat(sanitizeEditableIncomeInput(value))
}

function formatEditableCurrency(value) {
  const sanitizedValue = sanitizeEditableIncomeInput(value)
  const [integerPart = '0', decimalPart] = sanitizedValue.split('.')
  const formattedIntegerPart = Number(integerPart).toLocaleString('en-CA')

  if (sanitizedValue.endsWith('.')) {
    return `$${formattedIntegerPart}.`
  }

  if (decimalPart !== undefined) {
    return `$${formattedIntegerPart}.${decimalPart}`
  }

  return `$${formattedIntegerPart}`
}

function deriveNextScenario(currentScenario, change, maxSupportedChildren) {
  const { name, value, type, checked } = change

  if (name === 'useSeparateSpousalIncomes') {
    return { ...currentScenario, useSeparateSpousalIncomes: checked }
  }

  if (name === 'children') {
    const nextChildren = value
    const nextChildrenUnderSix = Math.min(
      Number(currentScenario.childrenUnderSix || 0),
      Number(nextChildren || 0),
    )
    return {
      ...currentScenario,
      children: nextChildren,
      childrenUnderSix: String(nextChildrenUnderSix),
    }
  }

  if (name === 'childrenUnderSix') {
    const boundedValue = Math.min(Math.max(Number(value || 0), 0), maxSupportedChildren)
    return {
      ...currentScenario,
      children: String(Math.max(Number(currentScenario.children || 0), boundedValue)),
      childrenUnderSix: String(boundedValue),
    }
  }

  return { ...currentScenario, [name]: type === 'checkbox' ? checked : value }
}

function scenarioHasRequiredFields(activeScenario) {
  const requiredFields = [
    activeScenario.children,
    activeScenario.childrenUnderSix,
    activeScenario.taxYear,
    activeScenario.payorIncome,
    activeScenario.recipientIncome,
    activeScenario.targetMinPercent,
    activeScenario.targetMaxPercent,
  ]

  return !requiredFields.some((value) => value === '')
}

function scaleConfig(configs, taxYear) {
  if (taxYear in configs) {
    return configs[taxYear]
  }

  const years = Object.keys(configs).map(Number)
  const sourceYear = taxYear < Math.min(...years) ? Math.min(...years) : Math.max(...years)
  const scale = resolveTaxYearIndexFactor(taxYear) / resolveTaxYearIndexFactor(sourceYear)
  const sourceConfig = configs[sourceYear]

  return Object.fromEntries(
    Object.entries(sourceConfig).map(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        if (key.endsWith('Rates')) {
          return [key, value]
        }

        return [
          key,
          Object.fromEntries(
            Object.entries(value).map(([nestedKey, nestedValue]) => [
              nestedKey,
              Number((nestedValue * scale).toFixed(2)),
            ]),
          ),
        ]
      }

      return [key, Number((value * scale).toFixed(2))]
    }),
  )
}

function calculateCanadaChildBenefit(income, numChildren, childrenUnderSix, taxYear) {
  if (numChildren <= 0) {
    return 0
  }

  const config = scaleConfig(ccbConfigs, taxYear)
  const cappedCount = Math.min(numChildren, ccbChildCountCap)
  const childrenOverSix = numChildren - childrenUnderSix
  const maximumBenefit = config.under6 * childrenUnderSix + config.age6To17 * childrenOverSix
  let reduction = 0

  if (income > config.threshold2) {
    reduction =
      config.step2Bases[cappedCount] + (income - config.threshold2) * config.step2Rates[cappedCount]
  } else if (income > config.threshold1) {
    reduction = (income - config.threshold1) * config.step1Rates[cappedCount]
  }

  return Number(Math.max(maximumBenefit - reduction, 0).toFixed(2))
}

function calculateGstHstCredit(income, registeredChildren, taxYear) {
  const config = scaleConfig(gstConfigs, taxYear)
  const subtotal =
    registeredChildren > 0
      ? config.baseCredit +
        config.baseCredit +
        config.childCredit * Math.max(registeredChildren - 1, 0) +
        config.singleSupplement
      : config.baseCredit +
        Math.min(
          config.singleSupplement,
          Math.max(income - config.singleSupplementThreshold, 0) * 0.02,
        )

  return Number(
    Math.max(subtotal - Math.max(income - config.phaseoutThreshold, 0) * 0.05, 0).toFixed(2),
  )
}

function calculateBcFamilyBenefitChildAmount(
  count,
  firstChildAmount,
  secondChildAmount,
  additionalChildAmount,
) {
  if (count <= 0) {
    return 0
  }
  if (count === 1) {
    return firstChildAmount
  }
  if (count === 2) {
    return firstChildAmount + secondChildAmount
  }

  return firstChildAmount + secondChildAmount + additionalChildAmount * (count - 2)
}

function calculateBcFamilyBenefit(income, registeredChildren, taxYear) {
  if (registeredChildren <= 0) {
    return 0
  }

  const config = scaleConfig(bcFamilyBenefitConfigs, taxYear)
  const maximumChildAmount = calculateBcFamilyBenefitChildAmount(
    registeredChildren,
    config.maxFirstChild,
    config.maxSecondChild,
    config.maxAdditionalChild,
  )
  const guaranteedMinimum = calculateBcFamilyBenefitChildAmount(
    registeredChildren,
    config.minFirstChild,
    config.minSecondChild,
    config.minAdditionalChild,
  )
  const maximumTotal = maximumChildAmount + config.singleParentSupplement

  if (income <= config.maxThreshold) {
    return Number(maximumTotal.toFixed(2))
  }
  if (income <= config.phaseoutThreshold) {
    return Number(
      Math.max(maximumTotal - (income - config.maxThreshold) * 0.04, guaranteedMinimum).toFixed(2),
    )
  }

  return Number(
    Math.max(guaranteedMinimum - (income - config.phaseoutThreshold) * 0.04, 0).toFixed(2),
  )
}

function calculateBcClimateActionCredit(income, registeredChildren, taxYear) {
  if (taxYear >= 2024) {
    return 0
  }

  const config = scaleConfig(bcClimateConfigs, taxYear)
  const threshold = registeredChildren > 0 ? config.familyThreshold : config.singleThreshold
  const maximumCredit =
    registeredChildren > 0
      ? config.adult +
        config.secondAdultOrFirstChild +
        config.additionalChild * Math.max(registeredChildren - 1, 0)
      : config.adult

  return Number(Math.max(maximumCredit - Math.max(income - threshold, 0) * 0.02, 0).toFixed(2))
}

function calculateSharedCustodyBenefits(payorIncome, recipientIncome, numChildren, childrenUnderSix, taxYear) {
  const multiplier = 0.5
  const buildBreakdown = (income) => {
    const canadaChildBenefitAnnual = calculateCanadaChildBenefit(
      income,
      numChildren,
      childrenUnderSix,
      taxYear,
    )
    const gstHstCreditAnnual = calculateGstHstCredit(income, numChildren, taxYear)
    const bcFamilyBenefitAnnual = calculateBcFamilyBenefit(income, numChildren, taxYear)
    const bcClimateActionCreditAnnual = calculateBcClimateActionCredit(income, numChildren, taxYear)

    return {
      canadaChildBenefitAnnual: Number((canadaChildBenefitAnnual * multiplier).toFixed(2)),
      gstHstCreditAnnual: Number((gstHstCreditAnnual * multiplier).toFixed(2)),
      bcFamilyBenefitAnnual: Number((bcFamilyBenefitAnnual * multiplier).toFixed(2)),
      bcClimateActionCreditAnnual: Number((bcClimateActionCreditAnnual * multiplier).toFixed(2)),
    }
  }

  const payor = buildBreakdown(payorIncome)
  const recipient = buildBreakdown(recipientIncome)

  return {
    payor: {
      ...payor,
      totalAnnual: Number(
        (
          payor.canadaChildBenefitAnnual +
          payor.gstHstCreditAnnual +
          payor.bcFamilyBenefitAnnual +
          payor.bcClimateActionCreditAnnual
        ).toFixed(2),
      ),
    },
    recipient: {
      ...recipient,
      totalAnnual: Number(
        (
          recipient.canadaChildBenefitAnnual +
          recipient.gstHstCreditAnnual +
          recipient.bcFamilyBenefitAnnual +
          recipient.bcClimateActionCreditAnnual
        ).toFixed(2),
      ),
    },
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error ?? 'Request failed.')
  }

  return data
}

function DetailList({ items, emphasis = false }) {
  return (
    <dl className={`detail-list${emphasis ? ' detail-list--emphasis' : ''}`}>
      {items.map((item) => (
        <div key={item.label} className="detail-list__row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function CurrencyCell({ value, signed = false }) {
  const amount = asNumber(value)
  const className = [
    'currency-cell',
    signed ? 'signed-value' : '',
    signed && amount > 0 ? 'signed-value--positive' : '',
    signed && amount < 0 ? 'signed-value--negative' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const content = signed ? formatSignedCurrency(amount) : formatCurrency(amount)

  return <span className={className}>{content}</span>
}

function InfoTooltip({ label, tooltipClassName = '', children }) {
  const className = ['info-icon', tooltipClassName].filter(Boolean).join(' ')

  return (
    <span className={className} tabIndex={0} aria-label={label}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M12 10v6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="12" cy="7" r="1" fill="currentColor" />
      </svg>
      <span className="info-tooltip" role="tooltip">
        {children}
      </span>
    </span>
  )
}

function NdiConvergenceChart({ history }) {
  const chartHistory = history.filter(
    (entry) => Number.isFinite(entry.ndiPayor) && Number.isFinite(entry.ndiRecipient),
  )
  if (chartHistory.length === 0) {
    return null
  }

  const width = 680
  const height = 280
  const padding = { top: 20, right: 24, bottom: 36, left: 80 }
  const iterations = chartHistory.map((entry) => entry.iteration)
  const ndiValues = chartHistory.flatMap((entry) => [entry.ndiPayor, entry.ndiRecipient])
  const minIteration = Math.min(...iterations)
  const maxIteration = Math.max(...iterations)
  const minValue = Math.min(...ndiValues)
  const maxValue = Math.max(...ndiValues)
  const valuePadding = Math.max((maxValue - minValue) * 0.08, 1000)
  const domainMin = minValue - valuePadding
  const domainMax = maxValue + valuePadding
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const xSpan = Math.max(maxIteration - minIteration, 1)
  const ySpan = Math.max(domainMax - domainMin, 1)
  const xAt = (iteration) => padding.left + ((iteration - minIteration) / xSpan) * plotWidth
  const yAt = (value) => padding.top + (1 - (value - domainMin) / ySpan) * plotHeight
  const toPoints = (key) =>
    chartHistory.map((entry) => `${xAt(entry.iteration)},${yAt(entry[key])}`).join(' ')
  const tickCount = 4
  const yTicks = Array.from({ length: tickCount + 1 }, (_, index) => {
    const value = domainMin + (ySpan * index) / tickCount
    return {
      value,
      y: yAt(value),
    }
  })
  const finalPoint = chartHistory[chartHistory.length - 1]
  const payorColor = '#7d4e2d'
  const recipientColor = '#2f6f5e'

  return (
    <figure className="convergence-chart">
      <figcaption>NDI convergence</figcaption>
      <div className="convergence-chart__legend" aria-hidden="true">
        <span className="convergence-chart__legend-item">
          <span
            className="convergence-chart__legend-swatch"
            style={{ backgroundColor: payorColor }}
          />
          Payor NDI
        </span>
        <span className="convergence-chart__legend-item">
          <span
            className="convergence-chart__legend-swatch"
            style={{ backgroundColor: recipientColor }}
          />
          Recipient NDI
        </span>
      </div>
      <svg
        className="convergence-chart__svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="NDI convergence chart"
      >
        <title>NDI convergence chart</title>
        {yTicks.map((tick) => (
          <g key={tick.value}>
            <line
              x1={padding.left}
              y1={tick.y}
              x2={width - padding.right}
              y2={tick.y}
              className="convergence-chart__grid-line"
            />
            <text
              x={padding.left - 10}
              y={tick.y + 4}
              textAnchor="end"
              className="convergence-chart__axis-label"
            >
              {formatCurrency(tick.value)}
            </text>
          </g>
        ))}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          className="convergence-chart__axis-line"
        />
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={height - padding.bottom}
          className="convergence-chart__axis-line"
        />
        <polyline
          fill="none"
          stroke={payorColor}
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={toPoints('ndiPayor')}
        />
        <polyline
          fill="none"
          stroke={recipientColor}
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={toPoints('ndiRecipient')}
        />
        <circle cx={xAt(finalPoint.iteration)} cy={yAt(finalPoint.ndiPayor)} r="4" fill={payorColor} />
        <circle
          cx={xAt(finalPoint.iteration)}
          cy={yAt(finalPoint.ndiRecipient)}
          r="4"
          fill={recipientColor}
        />
        <text
          x={Math.min(xAt(finalPoint.iteration) + 10, width - padding.right - 4)}
          y={yAt(finalPoint.ndiPayor) - 10}
          className="convergence-chart__series-label"
        >
          Payor {formatCurrency(finalPoint.ndiPayor)}
        </text>
        <text
          x={Math.min(xAt(finalPoint.iteration) + 10, width - padding.right - 4)}
          y={yAt(finalPoint.ndiRecipient) + 18}
          className="convergence-chart__series-label"
        >
          Recipient {formatCurrency(finalPoint.ndiRecipient)}
        </text>
        <text
          x={padding.left}
          y={height - 10}
          className="convergence-chart__axis-label"
        >
          Iteration {minIteration}
        </text>
        <text
          x={width - padding.right}
          y={height - 10}
          textAnchor="end"
          className="convergence-chart__axis-label"
        >
          Iteration {maxIteration}
        </text>
      </svg>
    </figure>
  )
}

function ResultTable({ caption, columns, rows, numericColumnIndexes = [] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th
                key={column}
                className={numericColumnIndexes.includes(index) ? 'data-table__numeric' : ''}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={typeof row[0] === 'object' && row[0] !== null ? row[0].key : row[0]}>
              {row.map((cell, index) => (
                <td
                  key={typeof cell === 'object' && cell !== null ? cell.key : `${row[0]}-${index}`}
                  className={`${numericColumnIndexes.includes(index) ? 'data-table__numeric' : ''} ${
                    typeof cell === 'object' && cell !== null && cell.className ? cell.className : ''
                  }`.trim()}
                >
                  {typeof cell === 'object' && cell !== null ? cell.content : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function App() {
  const [metadata, setMetadata] = useState(null)
  const [scenario, setScenario] = useState(defaultScenario)
  const [autoRecalculate, setAutoRecalculate] = useState(true)
  const [netIncomePeriod, setNetIncomePeriod] = useState('annual')
  const [spousalDetailsOpen, setSpousalDetailsOpen] = useState(false)
  const [childResult, setChildResult] = useState(null)
  const [spousalResult, setSpousalResult] = useState(null)
  const [childError, setChildError] = useState('')
  const [spousalError, setSpousalError] = useState('')
  const [metadataError, setMetadataError] = useState('')
  const [isCalculating, setIsCalculating] = useState(false)
  const [editingGrossIncome, setEditingGrossIncome] = useState(null)
  const requestSequence = useRef(0)
  const scenarioRef = useRef(defaultScenario)
  const maxSupportedChildren = Math.max(...(metadata?.supportedChildren ?? [7]))
  const spousalSupportJurisdictionCodes = new Set(
    (metadata?.spousalSupportJurisdictions ?? []).map((jurisdiction) => jurisdiction.code),
  )

  useEffect(() => {
    scenarioRef.current = scenario
  }, [scenario])

  useEffect(() => {
    let active = true

    async function loadMetadata() {
      const response = await fetch('/api/metadata')
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error ?? 'Unable to load calculator metadata.')
      }

      if (active) {
        setMetadata(data)
      }
    }

    loadMetadata().catch((error) => {
      if (active) {
        setMetadataError(error.message)
      }
    })

    return () => {
      active = false
    }
  }, [])

  async function submitScenario(activeScenario) {
    const requestId = requestSequence.current + 1
    requestSequence.current = requestId
    setIsCalculating(true)
    setChildError('')
    setSpousalError('')
    const spousalSupportAvailable = spousalSupportJurisdictionCodes.has(activeScenario.jurisdiction)

    const payload = {
      jurisdiction: activeScenario.jurisdiction,
      children: Number(activeScenario.children),
      childrenUnderSix: Number(activeScenario.childrenUnderSix),
      taxYear: Number(activeScenario.taxYear),
      payorIncome: Number(activeScenario.payorIncome),
      recipientIncome: Number(activeScenario.recipientIncome),
    }

    const [childResponse, spousalResponse] = await Promise.allSettled([
      postJson('/api/calculate/child-support', payload),
      spousalSupportAvailable
        ? postJson('/api/calculate/spousal-support', {
            ...payload,
            ...(activeScenario.useSeparateSpousalIncomes && activeScenario.payorSpousalIncome !== ''
              ? { payorSpousalIncome: Number(activeScenario.payorSpousalIncome) }
              : {}),
            ...(activeScenario.useSeparateSpousalIncomes && activeScenario.recipientSpousalIncome !== ''
              ? { recipientSpousalIncome: Number(activeScenario.recipientSpousalIncome) }
              : {}),
            ...(activeScenario.fixedTotalSupportAnnual !== ''
              ? { fixedTotalSupportAnnual: Number(activeScenario.fixedTotalSupportAnnual) }
              : {}),
            targetMinPercent: Number(activeScenario.targetMinPercent),
            targetMaxPercent: Number(activeScenario.targetMaxPercent),
          })
        : Promise.resolve(null),
    ])

    if (requestId !== requestSequence.current) {
      return
    }

    if (childResponse.status === 'fulfilled') {
      setChildResult(childResponse.value)
    } else {
      setChildResult(null)
      setChildError(childResponse.reason.message)
    }

    if (!spousalSupportAvailable) {
      setSpousalResult(null)
      setSpousalError(
        metadata?.spousalSupportAssumptions ??
          'Spousal support is currently available only for British Columbia.',
      )
    } else if (spousalResponse.status === 'fulfilled') {
      setSpousalResult(spousalResponse.value)
    } else {
      setSpousalResult(null)
      setSpousalError(spousalResponse.reason.message)
    }

    setIsCalculating(false)
  }

  const submitCurrentScenario = useEffectEvent(() => {
    if (!scenarioHasRequiredFields(scenario)) {
      return
    }

    void submitScenario(scenario)
  })

  useEffect(() => {
    if (!metadata || !autoRecalculate) {
      return
    }

    submitCurrentScenario()
  }, [autoRecalculate, metadata])

  function handleScenarioChange(event) {
    const nextScenario = deriveNextScenario(scenarioRef.current, event.target, maxSupportedChildren)
    scenarioRef.current = nextScenario
    setScenario(nextScenario)

    if (autoRecalculate && metadata && scenarioHasRequiredFields(nextScenario)) {
      void submitScenario(nextScenario)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitScenario(scenario)
  }

  function handleReset() {
    setEditingGrossIncome(null)
    scenarioRef.current = defaultScenario
    setScenario(defaultScenario)

    if (autoRecalculate && metadata && scenarioHasRequiredFields(defaultScenario)) {
      void submitScenario(defaultScenario)
    }
  }

  function beginGrossIncomeEdit(fieldName, annualValue) {
    const displayValue = netIncomePeriod === 'monthly' ? annualValue / 12 : annualValue
    setEditingGrossIncome({
      fieldName,
      rawValue: String(Math.round(displayValue)),
    })
  }

  function applyGrossIncomeEdit(fieldName, rawValue, finalize = false) {
    const parsedDisplayValue = parseEditableIncome(rawValue)
    if (!Number.isFinite(parsedDisplayValue) || parsedDisplayValue < 0) {
      return
    }

    const normalizedDisplayValue = finalize ? Math.round(parsedDisplayValue) : parsedDisplayValue
    const annualValue = netIncomePeriod === 'monthly' ? normalizedDisplayValue * 12 : normalizedDisplayValue
    const nextScenario = {
      ...scenarioRef.current,
      [fieldName]: String(annualValue),
    }

    scenarioRef.current = nextScenario
    setScenario(nextScenario)
    if (autoRecalculate && metadata && scenarioHasRequiredFields(nextScenario)) {
      void submitScenario(nextScenario)
    }
    if (finalize) {
      setEditingGrossIncome(null)
    }
  }

  function commitGrossIncomeEdit() {
    if (!editingGrossIncome) {
      return
    }

    applyGrossIncomeEdit(editingGrossIncome.fieldName, editingGrossIncome.rawValue, true)
  }

  const supportedChildren = metadata?.supportedChildren ?? []
  const childRows = childResult
    ? [
        ['Payor', formatCurrency(childResult.payorMonthly), formatCurrency(childResult.payorAnnual)],
        [
          'Recipient',
          formatCurrency(childResult.recipientMonthly),
          formatCurrency(childResult.recipientAnnual),
        ],
        ['Net transfer', formatCurrency(childResult.netMonthly), formatCurrency(childResult.netAnnual)],
      ]
    : []
  const payorGrossIncome = spousalResult ? asNumber(spousalResult.payorIncome) : 0
  const spousalSupportAnnual = spousalResult
    ? asNumber(spousalResult.estimatedSpousalSupportAnnual)
    : 0
  const childSupportAnnual = spousalResult
    ? asNumber(spousalResult.childSupport?.netAnnual)
    : 0
  const payorNdi = spousalResult ? asNumber(spousalResult.ndiPayor) : 0
  const activeTaxYear = spousalResult ? asNumber(spousalResult.taxYear, baseTaxYear) : baseTaxYear
  const recipientGrossIncome = spousalResult ? asNumber(spousalResult.recipientIncome) : 0
  const recipientNdi = spousalResult ? asNumber(spousalResult.ndiRecipient) : 0
  const benefitFallback = spousalResult
    ? calculateSharedCustodyBenefits(
        Math.max(payorGrossIncome - spousalSupportAnnual, 0),
        Math.max(recipientGrossIncome + spousalSupportAnnual, 0),
        asNumber(spousalResult.children, asNumber(scenario.children)),
        asNumber(spousalResult.childrenUnderSix, asNumber(scenario.childrenUnderSix)),
        activeTaxYear,
      )
    : null
  const payorBenefitBreakdown = spousalResult?.benefits?.payor ??
    benefitFallback?.payor ?? {
      canadaChildBenefitAnnual: 0,
      gstHstCreditAnnual: 0,
      bcFamilyBenefitAnnual: 0,
      bcClimateActionCreditAnnual: 0,
      totalAnnual: 0,
    }
  const recipientBenefitBreakdown = spousalResult?.benefits?.recipient ??
    benefitFallback?.recipient ?? {
      canadaChildBenefitAnnual: 0,
      gstHstCreditAnnual: 0,
      bcFamilyBenefitAnnual: 0,
      bcClimateActionCreditAnnual: 0,
      totalAnnual: 0,
    }
  const payorTaxAfterSupport = spousalResult
    ? asNumber(
        spousalResult.payorTax,
        calculateApproxBcTax(payorGrossIncome - spousalSupportAnnual, activeTaxYear),
      )
    : 0
  const payorTaxBeforeSupportDeduction = spousalResult
    ? asNumber(
        spousalResult.payorTaxBeforeSupportDeduction,
        calculateApproxBcTax(payorGrossIncome, activeTaxYear),
      )
    : 0
  const payorTaxDeductionBenefit = spousalResult
    ? asNumber(
        spousalResult.payorTaxDeductionBenefit,
        Math.max(payorTaxBeforeSupportDeduction - payorTaxAfterSupport, 0),
      )
    : 0
  const recipientGovernmentBenefits = spousalResult
    ? asNumber(recipientBenefitBreakdown.totalAnnual)
    : 0
  const recipientTaxBeforeSupportInclusion = spousalResult
    ? asNumber(
        spousalResult.recipientTaxBeforeSupportInclusion,
        calculateApproxBcTax(recipientGrossIncome, activeTaxYear),
      )
    : 0
  const recipientTaxSupportCost = spousalResult
    ? asNumber(
        spousalResult.recipientTaxSupportCost,
        Math.max(
          asNumber(
            spousalResult.recipientTax,
            calculateApproxBcTax(recipientGrossIncome + spousalSupportAnnual, activeTaxYear),
          ) - recipientTaxBeforeSupportInclusion,
          0,
        ),
      )
    : 0
  const payorNetIncome = spousalResult
    ? asNumber(
        spousalResult.actualNetIncomePayor,
        payorGrossIncome -
          payorTaxAfterSupport -
          spousalSupportAnnual -
          childSupportAnnual +
          payorBenefitBreakdown.totalAnnual,
      )
    : 0
  const recipientNetIncome = spousalResult
    ? asNumber(
        spousalResult.actualNetIncomeRecipient,
        recipientGrossIncome -
          (recipientTaxBeforeSupportInclusion + recipientTaxSupportCost) +
          spousalSupportAnnual +
          childSupportAnnual +
          recipientBenefitBreakdown.totalAnnual,
      )
    : 0
  const payorEquivalentBeforeTaxIncome = spousalResult
    ? calculateEquivalentBeforeTaxIncome(payorNetIncome, activeTaxYear)
    : 0
  const recipientEquivalentBeforeTaxIncome = spousalResult
    ? calculateEquivalentBeforeTaxIncome(recipientNetIncome, activeTaxYear)
    : 0
  const netIncomeDivisor = netIncomePeriod === 'monthly' ? 12 : 1
  const netIncomeColumnLabel = netIncomePeriod === 'monthly' ? 'Monthly amount' : 'Annual amount'
  const netIncomeRawRows = spousalResult
    ? [
        ['Gross income', payorGrossIncome, recipientGrossIncome],
        ['Child support', -childSupportAnnual, childSupportAnnual],
        ['Spousal support (pre-tax)', -spousalSupportAnnual, spousalSupportAnnual],
        ['Spousal support (tax deduction)', payorTaxDeductionBenefit, -recipientTaxSupportCost],
        [
          'Canada child benefit',
          payorBenefitBreakdown.canadaChildBenefitAnnual,
          recipientBenefitBreakdown.canadaChildBenefitAnnual,
        ],
        [
          'GST/HST credit',
          payorBenefitBreakdown.gstHstCreditAnnual,
          recipientBenefitBreakdown.gstHstCreditAnnual,
        ],
        [
          'B.C. family benefit',
          payorBenefitBreakdown.bcFamilyBenefitAnnual,
          recipientBenefitBreakdown.bcFamilyBenefitAnnual,
        ],
        ...((payorBenefitBreakdown.bcClimateActionCreditAnnual > 0 ||
        recipientBenefitBreakdown.bcClimateActionCreditAnnual > 0)
          ? [
              [
                'B.C. climate action credit',
                payorBenefitBreakdown.bcClimateActionCreditAnnual,
                recipientBenefitBreakdown.bcClimateActionCreditAnnual,
              ],
            ]
          : []),
        ['Income tax', -payorTaxBeforeSupportDeduction, -recipientTaxBeforeSupportInclusion],
        ['Estimated net income', payorNetIncome, recipientNetIncome],
        [
          'Equivalent before-tax income',
          payorEquivalentBeforeTaxIncome,
          recipientEquivalentBeforeTaxIncome,
        ],
      ]
    : []
  const unsignedNetIncomeLabels = new Set([
    'Gross income',
    'Estimated net income',
    'Equivalent before-tax income',
  ])
  const emphasizedNetIncomeLabels = new Set([
    'Child support',
    'Spousal support (pre-tax)',
    'Estimated net income',
  ])
  const netIncomeDisplayRows = netIncomeRawRows.map(([label, payorValue, recipientValue]) => {
    const scale = netIncomeDivisor
    const signed = !unsignedNetIncomeLabels.has(label)
    const isEquivalentIncomeRow = label === 'Equivalent before-tax income'
    const isEmphasizedRow = emphasizedNetIncomeLabels.has(label)
    const isGrossIncomeRow = label === 'Gross income'
    const rowClassName = [
      isEquivalentIncomeRow ? 'data-table__informational' : '',
      isEmphasizedRow ? 'data-table__emphasis' : '',
    ]
      .filter(Boolean)
      .join(' ')
    const labelCell = isEquivalentIncomeRow
      ? {
          key: `${label}-label`,
          className: rowClassName,
          content: (
            <span className="info-label">
              <em>{label}</em>
              <InfoTooltip label="Equivalent before-tax income explanation">
                <>
                  The gross employment income that would leave the same after-tax income if there
                  were no child support, spousal support, or government benefits.
                </>
              </InfoTooltip>
            </span>
          ),
        }
      : rowClassName
        ? {
            key: `${label}-label`,
            className: rowClassName,
            content: label,
          }
        : label

    return [
      labelCell,
      {
        key: `${label}-payor`,
        className: rowClassName,
        content:
          isGrossIncomeRow && editingGrossIncome?.fieldName === 'payorIncome' ? (
            <input
              className="data-table__input"
              type="text"
              inputMode="numeric"
              aria-label="Edit payor gross income"
              value={formatEditableCurrency(editingGrossIncome.rawValue)}
              size={Math.max(formatEditableCurrency(editingGrossIncome.rawValue).length, 2)}
              autoFocus
              onChange={(event) => {
                const rawValue = sanitizeEditableIncomeInput(event.target.value)
                setEditingGrossIncome((current) =>
                  current ? { ...current, rawValue } : current,
                )
                applyGrossIncomeEdit('payorIncome', rawValue)
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  commitGrossIncomeEdit()
                }
                if (event.key === 'Escape') {
                  setEditingGrossIncome(null)
                }
              }}
              onBlur={() => setEditingGrossIncome(null)}
            />
          ) : isGrossIncomeRow ? (
            <button
              type="button"
              className="data-table__cell-button"
              onDoubleClick={() => beginGrossIncomeEdit('payorIncome', payorGrossIncome)}
            >
              <CurrencyCell value={payorValue / scale} signed={signed} />
            </button>
          ) : (
            <CurrencyCell value={payorValue / scale} signed={signed} />
          ),
      },
      {
        key: `${label}-recipient`,
        className: rowClassName,
        content:
          isGrossIncomeRow && editingGrossIncome?.fieldName === 'recipientIncome' ? (
            <input
              className="data-table__input"
              type="text"
              inputMode="numeric"
              aria-label="Edit recipient gross income"
              value={formatEditableCurrency(editingGrossIncome.rawValue)}
              size={Math.max(formatEditableCurrency(editingGrossIncome.rawValue).length, 2)}
              autoFocus
              onChange={(event) => {
                const rawValue = sanitizeEditableIncomeInput(event.target.value)
                setEditingGrossIncome((current) =>
                  current ? { ...current, rawValue } : current,
                )
                applyGrossIncomeEdit('recipientIncome', rawValue)
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  commitGrossIncomeEdit()
                }
                if (event.key === 'Escape') {
                  setEditingGrossIncome(null)
                }
              }}
              onBlur={() => setEditingGrossIncome(null)}
            />
          ) : isGrossIncomeRow ? (
            <button
              type="button"
              className="data-table__cell-button"
              onDoubleClick={() =>
                beginGrossIncomeEdit('recipientIncome', recipientGrossIncome)
              }
            >
              <CurrencyCell value={recipientValue / scale} signed={signed} />
            </button>
          ) : (
            <CurrencyCell value={recipientValue / scale} signed={signed} />
          ),
      },
    ]
  })
  return (
    <div className="app-shell">
      <header className="toolbar">
        <div>
          <h1>Canadian Support Calculator</h1>
          <p>Child support for all non-Quebec jurisdictions. Spousal support currently British Columbia only.</p>
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar-panel">
          <section className="panel-section">
            <h2>Scenario</h2>
            <form className="scenario-form" onSubmit={handleSubmit}>
              <div className="form-grid">
                <label>
                  <span className="form-label-text">Jurisdiction</span>
                  <select
                    aria-label="Jurisdiction"
                    name="jurisdiction"
                    value={scenario.jurisdiction}
                    onChange={handleScenarioChange}
                  >
                    {(metadata?.jurisdictions ?? [{ code: 'BC', name: 'British Columbia' }]).map((jurisdiction) => (
                      <option key={jurisdiction.code} value={jurisdiction.code}>
                        {jurisdiction.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span className="form-label-text">
                    Children
                    <InfoTooltip label="Children information" tooltipClassName="info-icon--form">
                      <>Total number of children of the marriage for which child support is potentially payable.</>
                    </InfoTooltip>
                  </span>
                  <select
                    aria-label="Children"
                    name="children"
                    value={scenario.children}
                    onChange={handleScenarioChange}
                  >
                    {supportedChildren.map((count) => (
                      <option key={count} value={count}>
                        {count}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span className="form-label-text">
                    Children under 6
                    <InfoTooltip label="Children under 6 information" tooltipClassName="info-icon--form">
                      <>Total number of children of the marriage currently under the age of 6.</>
                    </InfoTooltip>
                  </span>
                  <input
                    aria-label="Children under 6"
                    name="childrenUnderSix"
                    type="number"
                    min="0"
                    max={maxSupportedChildren}
                    step="1"
                    value={scenario.childrenUnderSix}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  <span className="form-label-text">
                    Tax year
                    <InfoTooltip label="Tax year information" tooltipClassName="info-icon--form">
                      <>
                        Use the tax tables for this year in calculating the various tax deductions and
                        credits that go into support calculations.
                      </>
                    </InfoTooltip>
                  </span>
                  <input
                    aria-label="Tax year"
                    name="taxYear"
                    type="number"
                    min="1"
                    step="1"
                    value={scenario.taxYear}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  <span className="form-label-text">
                    Payor income
                    <InfoTooltip label="Payor income information" tooltipClassName="info-icon--form">
                      <>
                        <p>
                          Enter the gross pre-tax income of the payor of support. Line <strong>15000</strong> of the
                          most recent T1 Income Tax Return (or notice of assessment) is typically used. The Guidelines
                          use gross income because net income allows discretionary deductions that could distort
                          fairness, and the tables already account for taxes.
                        </p>
                        <p><strong>When the Gross Income Amount Needs Adjustment</strong></p>
                        <ul>
                          <li><strong>Fluctuating income:</strong> Average income over the last 3 years.</li>
                          <li><strong>Income has changed since last filing:</strong> Use pay slips and current records.</li>
                          <li><strong>One-time amounts (e.g., bonus):</strong> May include all or part.</li>
                          <li><strong>Non-recurring capital/business losses:</strong> May be adjusted.</li>
                          <li>
                            <strong>Corporation director/officer/shareholder:</strong> Must include money available
                            from the corporation (pre-tax corporate income or imputed salary for services).
                          </li>
                          <li>
                            <strong>RRSP/pension income:</strong> Cannot deduct RRSP contributions; one-time
                            withdrawals may be excluded case by case.
                          </li>
                        </ul>
                        <p>
                          <strong>Note:</strong> The payor&apos;s income for the purpose of spousal support
                          calculations may be different from that used for the calculation of child support.
                          Generally, the income at the time of separation is used and, to the extent that income
                          has risen since that time, increases in income resulting from promotions, salary
                          increases, and other new sources of income that the person was not reasonably expected
                          to receive in the years following separation are excluded. In practical terms, this can
                          mean that we fix income at the gross level at the time of separation and then inflate
                          it by the rate of inflation since that time.
                        </p>
                      </>
                    </InfoTooltip>
                  </span>
                  <input
                    aria-label="Payor income"
                    name="payorIncome"
                    type="number"
                    min="0"
                    step="100"
                    value={scenario.payorIncome}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  <span className="form-label-text">
                    Recipient income
                    <InfoTooltip label="Recipient income information" tooltipClassName="info-icon--form">
                      <>
                        <p>
                          Enter the gross pre-tax income of the recipient of support. Line <strong>15000</strong> of
                          the most recent T1 Income Tax Return (or notice of assessment) is typically used. The
                          Guidelines use gross income because net income allows discretionary deductions that could
                          distort fairness, and the tables already account for taxes.
                        </p>
                        <p><strong>When the Gross Income Amount Needs Adjustment</strong></p>
                        <ul>
                          <li><strong>Fluctuating income:</strong> Average income over the last 3 years.</li>
                          <li><strong>Income has changed since last filing:</strong> Use pay slips and current records.</li>
                          <li><strong>One-time amounts (e.g., bonus):</strong> May include all or part.</li>
                          <li><strong>Non-recurring capital/business losses:</strong> May be adjusted.</li>
                          <li>
                            <strong>Corporation director/officer/shareholder:</strong> Must include money available
                            from the corporation (pre-tax corporate income or imputed salary for services).
                          </li>
                          <li>
                            <strong>RRSP/pension income:</strong> Cannot deduct RRSP contributions; one-time
                            withdrawals may be excluded case by case.
                          </li>
                        </ul>
                        <p>
                          <strong>Note:</strong> The recipient&apos;s income for the purpose of spousal support
                          calculations may be different from that used for the calculation of child support.
                          Generally, the income at the time of separation is used and, to the extent that income
                          has risen since that time, increases in income resulting from promotions, salary
                          increases, and other new sources of income that the person was not reasonably expected
                          to receive in the years following separation are excluded. In practical terms, this can
                          mean that we fix income at the gross level at the time of separation and then inflate
                          it by the rate of inflation since that time.
                        </p>
                      </>
                    </InfoTooltip>
                  </span>
                  <input
                    aria-label="Recipient income"
                    name="recipientIncome"
                    type="number"
                    min="0"
                    step="100"
                    value={scenario.recipientIncome}
                    onChange={handleScenarioChange}
                  />
                </label>

                <div className="scenario-drawer-toggle">
                  <label className="form-toggle">
                    <input
                      aria-label="Use different incomes for spousal support only"
                      name="useSeparateSpousalIncomes"
                      type="checkbox"
                      checked={scenario.useSeparateSpousalIncomes}
                      onChange={handleScenarioChange}
                    />
                    <span>Use different incomes for spousal support only</span>
                  </label>
                </div>

                <div
                  className={`scenario-drawer ${
                    scenario.useSeparateSpousalIncomes ? 'scenario-drawer--open' : 'scenario-drawer--closed'
                  }`}
                >
                  <div className="scenario-drawer__content">
                    <p>
                      Optional separation-era gross incomes for spousal support only. Child support
                      continues to use the main current gross incomes above.
                    </p>

                    <label>
                      <span className="form-label-text">Payor income for spousal support only</span>
                      <input
                        aria-label="Payor income for spousal support only"
                        name="payorSpousalIncome"
                        type="number"
                        min="0"
                        step="100"
                        disabled={!scenario.useSeparateSpousalIncomes}
                        value={scenario.payorSpousalIncome}
                        onChange={handleScenarioChange}
                      />
                    </label>

                    <label>
                      <span className="form-label-text">Recipient income for spousal support only</span>
                      <input
                        aria-label="Recipient income for spousal support only"
                        name="recipientSpousalIncome"
                        type="number"
                        min="0"
                        step="100"
                        disabled={!scenario.useSeparateSpousalIncomes}
                        value={scenario.recipientSpousalIncome}
                        onChange={handleScenarioChange}
                      />
                    </label>

                    <label>
                      <span className="form-label-text">Fixed total gross support (annual)</span>
                      <input
                        aria-label="Fixed total gross support (annual)"
                        name="fixedTotalSupportAnnual"
                        type="number"
                        min="0"
                        step="100"
                        value={scenario.fixedTotalSupportAnnual}
                        onChange={handleScenarioChange}
                      />
                    </label>
                  </div>
                </div>

                <label>
                  <span className="form-label-text">
                    Target minimum %
                    <InfoTooltip label="Target minimum percentage information" tooltipClassName="info-icon--form">
                      <>
                        This is the minimum share of total net disposable income (NDI) of the payor and recipient that
                        the recipient will receive after child and spousal support and government taxes and credits.
                        Typically, this value is 40%.
                      </>
                    </InfoTooltip>
                  </span>
                  <input
                    aria-label="Target minimum %"
                    name="targetMinPercent"
                    type="number"
                    min="1"
                    max="99"
                    step="0.5"
                    value={scenario.targetMinPercent}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  <span className="form-label-text">
                    Target maximum %
                    <InfoTooltip label="Target maximum percentage information" tooltipClassName="info-icon--form">
                      <>
                        This is the maximum share of total net disposable income (NDI) of the payor and recipient that
                        the recipient will receive after child and spousal support and government taxes and credits.
                        Typically, this value is 46%.
                      </>
                    </InfoTooltip>
                  </span>
                  <input
                    aria-label="Target maximum %"
                    name="targetMaxPercent"
                    type="number"
                    min="1"
                    max="99"
                    step="0.5"
                    value={scenario.targetMaxPercent}
                    onChange={handleScenarioChange}
                  />
                </label>
              </div>

              <div className="form-actions">
                <label className="form-toggle">
                  <input
                    name="autoRecalculate"
                    type="checkbox"
                    checked={autoRecalculate}
                    onChange={(event) => setAutoRecalculate(event.target.checked)}
                  />
                  <span>Recalculate automatically</span>
                </label>
                <button type="submit" disabled={isCalculating || autoRecalculate}>
                  {isCalculating ? 'Calculating' : 'Recalculate'}
                </button>
                <button type="button" className="button-secondary" onClick={handleReset}>
                  Restore example
                </button>
              </div>
            </form>
          </section>
        </aside>

        <section className="results-panel">
          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Net Income</h2>
                <p>Estimated annual income after tax, child support, spousal support, and benefits.</p>
              </div>
              <div className="view-toggle" role="group" aria-label="Net income period">
                <button
                  type="button"
                  className={netIncomePeriod === 'annual' ? 'is-active' : ''}
                  aria-pressed={netIncomePeriod === 'annual'}
                  onClick={() => setNetIncomePeriod('annual')}
                >
                  Annual
                </button>
                <button
                  type="button"
                  className={netIncomePeriod === 'monthly' ? 'is-active' : ''}
                  aria-pressed={netIncomePeriod === 'monthly'}
                  onClick={() => setNetIncomePeriod('monthly')}
                >
                  Monthly
                </button>
              </div>
            </div>

            {spousalError ? <p className="error-text">{spousalError}</p> : null}

            {spousalResult ? (
              <ResultTable
                caption="Net income calculation"
                columns={['Component', `Payor ${netIncomeColumnLabel}`, `Recipient ${netIncomeColumnLabel}`]}
                rows={netIncomeDisplayRows}
                numericColumnIndexes={[1, 2]}
              />
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>

          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Calculation Details</h2>
                <p>Child support and spousal-support iteration details for the current scenario.</p>
              </div>
              <button
                type="button"
                className="drawer-toggle"
                aria-expanded={spousalDetailsOpen}
                onClick={() => setSpousalDetailsOpen((current) => !current)}
              >
                {spousalDetailsOpen ? 'Hide Details' : 'Show Details'}
              </button>
            </div>

            {childError ? <p className="error-text">{childError}</p> : null}

            {childResult || spousalResult ? (
              <div
                className={`details-drawer ${spousalDetailsOpen ? 'details-drawer--open' : 'details-drawer--closed'}`}
              >
                <div className="details-drawer__content">
                  {childResult ? (
                    <section className="details-block">
                      <div className="details-block__header">
                        <h3>Child support</h3>
                        <strong>{formatCurrency(childResult.netMonthly)}</strong>
                      </div>
                      <p>Monthly table amounts with offset calculation.</p>
                      <DetailList
                        emphasis
                        items={[
                          {
                            label: 'Transfer direction',
                            value:
                              childResult.direction === 'payor_to_recipient'
                                ? 'Payor to recipient'
                                : childResult.direction === 'recipient_to_payor'
                                  ? 'Recipient to payor'
                                  : 'No transfer',
                          },
                          { label: 'Net monthly transfer', value: formatCurrency(childResult.netMonthly) },
                          { label: 'Net annual transfer', value: formatCurrency(childResult.netAnnual) },
                        ]}
                      />
                      <ResultTable
                        caption="Child support amounts"
                        columns={['Party', 'Monthly', 'Annual']}
                        rows={childRows}
                        numericColumnIndexes={[1, 2]}
                      />
                    </section>
                  ) : null}

                  {spousalResult ? (
                    <section className="details-block">
                      <div className="details-block__header">
                        <h3>Spousal support calculations</h3>
                        <strong>{formatCurrency(spousalResult.estimatedSpousalSupportMonthly)}</strong>
                      </div>
                      <p>Iteration details used to place the recipient inside the selected NDI range.</p>
                      <DetailList
                        emphasis
                        items={[
                          {
                            label: 'Payor income used for spousal support',
                            value: formatCurrency(spousalResult.payorSpousalIncome ?? spousalResult.payorIncome),
                          },
                          {
                            label: 'Recipient income used for spousal support',
                            value: formatCurrency(
                              spousalResult.recipientSpousalIncome ?? spousalResult.recipientIncome,
                            ),
                          },
                          {
                            label: 'Estimated monthly spousal support',
                            value: formatCurrency(spousalResult.estimatedSpousalSupportMonthly),
                          },
                          {
                            label: 'Estimated annual spousal support',
                            value: formatCurrency(spousalResult.estimatedSpousalSupportAnnual),
                          },
                          ...(spousalResult.fixedTotalSupportAnnual != null
                            ? [
                                {
                                  label: 'Fixed total gross support',
                                  value: formatCurrency(spousalResult.fixedTotalSupportAnnual),
                                },
                              ]
                            : []),
                          {
                            label: 'Recipient share of NDI',
                            value: formatPercent(spousalResult.recipientSharePercent),
                          },
                          {
                            label: 'Iterations',
                            value: String(spousalResult.iterations),
                          },
                        ]}
                      />
                      <ResultTable
                        caption="Net disposable income"
                        columns={['Party', 'NDI']}
                        rows={[
                          ['Payor', formatCurrency(payorNdi)],
                          ['Recipient', formatCurrency(recipientNdi)],
                          [
                            'Child support annual',
                            formatCurrency(
                              spousalResult.ndiChildSupport?.netAnnual ?? spousalResult.childSupport.netAnnual,
                            ),
                          ],
                          ['Recipient benefits annual', formatCurrency(recipientGovernmentBenefits)],
                        ]}
                        numericColumnIndexes={[1]}
                      />
                      <NdiConvergenceChart history={spousalResult.history} />
                    </section>
                  ) : null}
                </div>
              </div>
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>

        </section>

        <section className="panel-section workspace__full">
          <h2>References</h2>
          <DetailList
            items={[
              {
                label: 'Supported child counts',
                value: supportedChildren.length ? supportedChildren.join(', ') : 'Loading',
              },
              {
                label: 'Target range',
                value: `${scenario.targetMinPercent}% to ${scenario.targetMaxPercent}% recipient NDI`,
              },
              {
                label: 'Children under 6',
                value: scenario.childrenUnderSix,
              },
              {
                label: 'Tax year',
                value: scenario.taxYear,
              },
              {
                label: 'Data note',
                value: metadata?.disclaimer ?? 'Loading',
              },
              {
                label: 'Benefit assumptions',
                value: metadata?.benefitAssumptions ?? 'Loading',
              },
              {
                label: 'Children note',
                value: metadata?.supportedChildrenNote ?? 'Loading',
              },
            ]}
          />
          {metadataError ? <p className="error-text">{metadataError}</p> : null}
        </section>
      </main>
    </div>
  )
}

export default App
